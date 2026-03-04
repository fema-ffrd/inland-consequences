import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
from scipy.stats import norm
import math
import os
import csv
from re import sub
import sys

logger = logging.getLogger("pfraCoastal")

class _PFRACoastal_Lib:
    def __init__(self) -> object:
        pass
    
    #####################
    # adjust_Loss_DEDLIM1()
    #	adjusts raw loss values for insurance deductible and limit.
    #	adjusted loss = raw loss minus the deductible, then capped at limit.
    # in:
    #	loss = raw loss value
    #	ded = deductible
    #	lim = limit
    # out:
    #	adjusted loss
    # called by:
    #	runMC_AALU_x4()
    # calls:
    #	NULL
    def adjust_Loss_DEDLIM1(self, loss: int, ded=0, lim=100_000_000) -> int:
        dLoss = loss - ded
        if dLoss < 0:
            dLoss = 0
        lLoss = min([val for val in [dLoss,lim] if val not in (np.nan, None)])
        return lLoss
    # Example,
    ## 
    # > bldg_loss = 25_000
    # > bldg_ded = 5000
    # > bldg_lim = 250_000
    # > adjust_Loss_DEDLIM1(bldg_loss, bldg_ded, bldg_lim)
    ## [1] 20000
    
    ####################
    # removeNonNumeric()
    #	function to remove non-numeric characters, except '.' and '-', from a string
    # IN:
    #	inText = text string
    # OUT:
    #	the same text string minus non-numeric characters other than '.' and '-'
    # called by:
    # 	getCurveByDDFid()
    #	runMC_AAL_x4()
    #	buildBldgFloodDepthTable5()
    # calls:
    #	NULL
    def removeNonNumeric(self, inText: str) -> str:
        outText = sub("[^0-9.-]", "", inText)
        return outText
    
    ###################
    # getZscore()
    # in:
    #	x = data value
    #	mean_data = mean of data
    #	sd_data = 1 std dev of data
    # out:
    #	zscore
    # called by:
    # 	main()
    # calls:
    #	NULL
    def getZscore(self, x: float, mean_data: float, sd_data: float) -> float:
        return (x - mean_data) / sd_data
    
    ####################
    # padTrailingSpaces()
    #	function to add trailing spaces to a given string to produce
    #	a new string of desired length
    #	If length of string is greater than or equal to desired length, then
    #	no padding will be added, and original string is returned
    # IN:
    #	inText = text string
    #	tLength = desired length of string
    # OUT:
    #	the same text string with spaces added to end
    # called by:
    #	GUI/setBLDGAttributes()
    # calls:
    #	NULL
    def padTrailingSpaces(self, inText: str, tLength=0) -> str:
        l = len(inText)
        if l >= tLength:
            outText = inText
        else:
            outText = ''.join([inText, (tLength - l)*' '])
        return outText
    
    ####################
    # write_log()
    # 	function to dump message ocntents to both the screen and the log file
    # In:
    #	txt = message to be written
    # Out:
    #	NULL
    # Calls:
    #	NULL
    def write_log(self, txt: str) -> None:
        logger.info(txt)
    
    ####################
    # validateBuildingAttr()
    #	function to test the attribute table of a building dataset in order 
    #	to determine if 
    #		the required fields exist,
    #		the fields contain the correct type (numeric vs character) of data
    #		field contains valid data
    #	If required fields are missing, they will be created an populated with default value
    #	If required fields contain unexpected values (inc NULLS), they will be replaced by the default
    #	*The table Inputs.bldg_attr_map contains the information about required field names, domains, and defaults
    # In:
    #   inputs = instance of pfracoastal.Inputs
    #	intab = attribute table from building dataset
    # Out:
    #	validated building attribute table 
    # called by:
    #	formatBuildings()
    # calls:
    #	NULL
    def validateBuildingAttr(self, inputs, intab: pd.DataFrame) -> pd.DataFrame:
        self.write_log(".start b validation.")
        
        # initialize attribute error flags as FALSE
        val_flag = [False for i in range(inputs.bldg_attr_map.shape[0])]
        
        self.write_log(".casting numeric fields.")
        # Replace non-numeric values for numeric-type attributes with the default value
        sel = inputs.bldg_attr_map.query("CHECK == 1 and (TYPE == 'int32' or TYPE == 'float64')").index.to_list()
        for i in sel:
            intab.iloc[:,i] = intab.iloc[:,i].astype(inputs.bldg_attr_map.at[i,"TYPE"])
            self.write_log(f".Check {inputs.bldg_attr_map.at[i,"IN"]}.")
            
            pre_mask_col = intab.iloc[:,i]
            intab.iloc[:,i] = intab.iloc[:,i].mask(intab.iloc[:,i].isna(), inputs.bldg_attr_map["DEF"].astype(inputs.bldg_attr_map.at[i,"TYPE"]).at[i])
            post_mask_col = intab.iloc[:,i]
            
            if pre_mask_col.ne(post_mask_col, fill_value=-8888).any(): # fill value here is arbitrary, just can't be a default value
                val_flag[i] = True
        
        self.write_log(".checking domained fields.")
        # Fix Domained Variables
        sel = inputs.bldg_attr_map[inputs.bldg_attr_map["DOM"].notna()].index.to_list()
        for i in sel:
            self.write_log(f".Check {inputs.bldg_attr_map.at[i,"IN"]}.")

            domain_val_list = [int(char) if char.isnumeric() else '' for char in list(inputs.bldg_attr_map.at[i,"DOM"]) if char.isnumeric()]

            pre_where_col = intab.iloc[:,i]
            intab.iloc[:,i] = intab.iloc[:,i].where(intab.iloc[:,i].isin(domain_val_list), inputs.bldg_attr_map["DEF"].astype(inputs.bldg_attr_map.at[i,"TYPE"]).at[i])
            post_where_col = intab.iloc[:,i]
            
            if pre_where_col.ne(post_where_col, fill_value=-8888).any(): # fill value here is arbitrary, just can't be a default value
                val_flag[i] = True
        
        bsmt_finish_type_index = inputs.bldg_attr_map.query("DESC == 'basement finish type'").index[0]
        fndn_type_index = inputs.bldg_attr_map.query("DESC == 'foundation type'").index[0]
        
        # check if basements have non basement finishes
        sel = intab.query(f"({intab.columns[bsmt_finish_type_index]}==0) and ({intab.columns[fndn_type_index]}==2)").index.to_list()
        if len(sel) > 0:
            self.write_log(f"Warning. {len(sel)} instances of foundation type 2 incorrectly paired with basement finish type 0. Substituting basement finish type 1.")
            intab.iloc[sel,bsmt_finish_type_index] = 1
        
        # check if non-basements have basement finishes
        sel = intab.query(f"({intab.columns[bsmt_finish_type_index]}!=0) and ({intab.columns[fndn_type_index]}!=2)").index.to_list()
        if len(sel) > 0:
            self.write_log(f"Warning. {len(sel)} instances of basement finish types 1,2 incorrectly paired with foundation type other than 2. Substituting basement finish type 0.")
            intab.iloc[sel,bsmt_finish_type_index] = 0
        
        # report valflags
        self.write_log(".snitching on b.")
        for i in range(len(val_flag)):
            if val_flag[i]:
                self.write_log(f"Invalid values of building attribute {inputs.bldg_attr_map.at[i,"IN"]} found. Replaced with value {inputs.bldg_attr_map.at[i,"DEF"]}")
        
        self.write_log(".finish b validation.")
        return intab
    
    ####################
    # get_NNx()
    # 	given single point coordinate (a), 
    #		find the nearest x points of a collection of point coordinates (b)
    #	Points should be in same CRS/projection
    # IN:
    #	b.coords = nx2 matrix of x,y coordinates for n points
    #	a.coord = a 1x2 matrix of a single x,y coordinate
    #	x = number of nearest neights to find, default = 3
    # OUT:
    #	(x)by2 df with row number of nearest point
    # called by:
    #	attachWSELtoBUILDING3()
    # calls:
    #	NULL
    def get_NNx(self, b_coords: np.ndarray, a_coord: np.ndarray, x=3) -> pd.DataFrame:
        nn_dist = scipy.spatial.distance.cdist(b_coords, a_coord, metric='euclidean')
        nn_res = pd.DataFrame(nn_dist, columns=['NN.dist'])
        nn_res['rowid'] = list(range(nn_dist.shape[0]))
        
        #get rowids for the three min distances
        nn_res.sort_values(by='NN.dist', axis=0, inplace=True)
        return nn_res.head(x)
    
    ####################
    # haltscript()
    #	function to halt the execution of the script.
    # called by:
    # 	formatSurge()
    #	formatBuildings()
    # calls:
    #	NULL
    def haltscript(self) -> None:
        self.write_log(".stopping execution.")
        logging.shutdown()
        sys.exit("Script was halted.")
    
    ####################
    # formatBuildings()
    #	given a path to a building shapefile,
    #	the shapefile will be read/loaded, with attributes formatted and validated
    # In:
    #	inputs = instance of pfracoastal.Inputs
    # Out:
    #	Geopandas GeodataFrame of building dataset
    # called by:
    #	main()
    # calls:
    #	validateBuildingAttr()
    #	haltscript()
    def formatBuildings(self, inputs) -> gpd.GeoDataFrame:
        # load buildings shape
        self.write_log(".loading building shapefile.")
        try:
            b_shp = gpd.read_file(inputs.bldg_path)
            shp_crs = b_shp.crs
        except Exception:
            cond = sys.exc_info()[1]
            self.write_log(f"Critical Error loading building shapefile, {inputs.bldg_path}")
            self.write_log("Here's the original error message:")
            self.write_log(cond.args[0])
            self.haltscript()
        
        self.write_log(".reformatting building table.")
        # pull attribute table
        b_tab = b_shp.to_wkb()
        
        # get geometry data from attribute table
        geom_data_wkb = b_tab.loc[:,'geometry']
        
        # add unique building ID
        b_tab["BID"] = pd.Series(list(range(1,b_tab.shape[0]+1)), dtype='int32')
        
        # find required attributes and make them if they dont exist
        for att in inputs.bldg_attr_map["IN"].to_list():
            if att not in b_tab.columns:
                self.write_log(f".creating undefined attribute, {att}")
                b_tab[att] = [np.nan for i in range(b_tab.shape[0])]
        
        # filter and sort incoming attributes
        b_tab = b_tab.loc[:,inputs.bldg_attr_map["IN"].to_list()]
        
        # map new attribute names
        b_tab = b_tab.rename(columns={new:old for new,old in list(zip(inputs.bldg_attr_map["IN"].to_list(), inputs.bldg_attr_map["OUT"].to_list()))})
        
        # validate
        self.write_log(".validate buildings.")
        try:
            b_tab = self.validateBuildingAttr(inputs, b_tab)
        except:
            cond = sys.exc_info()[1]
            self.write_log(f"Critical Error validating shapefile, {inputs.bldg_path}")
            self.write_log("Here's the original error message:")
            self.write_log(cond.args[0])
            self.haltscript()
        
        # export buildings to GeoDataFrame
        self.write_log(".packaging buildings.")
        geom_data_gs = gpd.GeoSeries.from_wkb(geom_data_wkb, crs=shp_crs)
        out_gdf = gpd.GeoDataFrame(b_tab, geometry=geom_data_gs, crs=shp_crs)
        return out_gdf
    
    #####################
    # DecideDDF_Task4()
    #	For use with CPFRA DDFs only
    #	decision tree to determine an appropriate DDF to use in high wave scenarios given foundation type
    # in:
    #	numStor = Number of stories	
    #	fndtn = foundation type = {2 = basement; 4 = crawlspace; 6 = pier; 7 = fill or wall; 8 = slab; 9 = pile}
    #	basefin = basement finish, if basement exists = {2 = finished; 1 = no finish; 0 = no basement}
    #	wvh = estimated breaking wave height (ft)
    # out:
    #	depth damage function ID to be used
    # called by:
    #	assign_TASK4_DDFs()
    # calls:
    #	NULL
    def DecideDDF_Task4(self, numStor:int, fndtn:int, basefin:int, wvh:float) -> str:        
        # check basefin
        chk = lambda x: x if x in (0,1,2) else 0
        basefin = chk(basefin)
        
        ##determine 1st digit
        # x = numStor
        calc_digit1 = lambda x: 1 if x==1 else 2
        digit1 = calc_digit1(numStor)
        
        ##determine 2nd digit
        # x = fndtn
        calc_digit2 = lambda x: 9 if x==9 else 2 if x==2 else 4
        digit2 = calc_digit2(fndtn)
        
        ##determine 3rd digit
        # x = fndtn, y = basefin
        calc_digit3 = lambda x,y: 1 if x==2 and y==0 else y if x==2 and y!=0 else 0
        digit3 = calc_digit3(fndtn, basefin)
        
        # determine 4th digit
        calc_digit4 = lambda x: 0 if x<0 else 1 if x<1 else 2 if x<3 else 3
        digit4 = calc_digit4(wvh)
        
        return ''.join([str(digit) for digit in (digit1,digit2,digit3,digit4)])
    # Example,
    ## 
    # > tempstories = 2
    # > tempfound = 9
    # > tempbase = 0
    # > tempwave = 3.1 
    # > DecideDDF4 (tempstories, tempfound, tempbase, tempwave)
    ## [1] "2903"

    #############
    # assign_TASK4_DDFs()
    # wrapper function to identify necessary fields in building table to determine the proper Task4 DDF 
    #	for each building.  And re-format results.
    # in: 
    #   inputs =
    #   b_tab = bldg_tab with only the records corresponding to valid buildings
    # out:
    #	ddf.tab = table with a row corresonding to each row in the input bldg.tab, with fields:
    #		DDF1 = freshwater Task4 DDF ID
    #		DDF2 = saltwater, low wave (<1 ft) scenario Task4 DDF ID
    #		DDF3 = saltwater, med wave (>=1 and <3 ft) scenario Task4 DDF ID
    #		DDF4 = saltwater, high wave (>=3ft) scenario Task4 DDF ID
    # called by:
    #	main()
    # calls:
    #	DecideDDF_Task4()
    def assign_TASK4_DDFs(self, inputs, b_tab: pd.DataFrame) -> pd.DataFrame:
        # record the necessary building fields to determine Task4 DDFs
        tddf_rows = inputs.bldg_attr_map.loc[inputs.bldg_attr_map["TDDF"]==1]
        fieldIndecies = [b_tab.columns.get_loc(f) for f in tddf_rows.loc[:,"OUT"].to_list()]
        
        self.write_log(".determining freshwater Task4 DDFs.")
        ddf1 = b_tab.iloc[:,fieldIndecies].apply(func=lambda x: self.DecideDDF_Task4(x.iat[0], x.iat[1], x.iat[2], -1), axis=1, result_type='reduce')

        self.write_log(".determining low-wave Task4 DDFs.")
        ddf2 = b_tab.iloc[:,fieldIndecies].apply(func=lambda x: self.DecideDDF_Task4(x.iat[0], x.iat[1], x.iat[2], 0.5), axis=1, result_type='reduce')
        
        # if waves are used in analysis, identify a second high-wave DDF else just copy the low-wave DDF
        if inputs.use_waves or inputs.use_twl:
            self.write_log(".determining med-wave Task4 DDFs.")
            ddf3 = b_tab.iloc[:,fieldIndecies].apply(func=lambda x: self.DecideDDF_Task4(x.iat[0], x.iat[1], x.iat[2], 2), axis=1, result_type='reduce')
            
            self.write_log(".determining high-wave Task4 DDFs.")
            ddf4 = b_tab.iloc[:,fieldIndecies].apply(func=lambda x: self.DecideDDF_Task4(x.iat[0], x.iat[1], x.iat[2], 4), axis=1, result_type='reduce')
        else:
            ddf3 = ddf2
            ddf4 = ddf2
        
        ddf_data = {
            "DDF1":ddf1,
            "DDF2":ddf2,
            "DDF3":ddf3,
            "DDF4":ddf4
        }
        
        ddf_tab = pd.DataFrame(ddf_data)
        return ddf_tab
            
    ####################
    # validateSurgeAttr2()
    #	function to test the attribute table of a surge dataset in order 
    #	to determine if 
    #		the required fields exist,
    #		the fields contain the correct type (numeric vs character) of data
    #		the fields contain valid data
    #	If required fields are missing, they will be created an populated with default value
    #	If required fields contain unexpected values (inc NULLS), they will be replaced by the defalt
    # In:
    #	intab = geodataframe from surge/wave dataset
    #	this_attr_map = pandas dataframe of SWEL data, loaded from the surge/wave datasets
    # Out:
    #	validated surge/wave attribute table 
    # called by:
    #	formatSurge()
    # calls:
    #	NULL
    def validateSurgeAttr2(self, intab:gpd.GeoDataFrame, this_att_map:pd.DataFrame) -> gpd.GeoDataFrame:
        
        self.write_log('.start s validation')
        # initialize attribute error flags as FALSE
        # Create a series of False values the number of rows in the dataframe
        valflag = pd.Series(False, index=this_att_map.index)
        
        self.write_log('.cast numeric fields.')
        # Replace non-numeric values for numeric-type attributes with the default value
        sel = this_att_map.index[this_att_map["CHECK"].astype(int) == 1].tolist()
        for i in sel:
            self.write_log(f".Check {this_att_map['OUT'].iloc[i]}.")
            # Force column to be numeric
            intab.iloc[:,i] = pd.to_numeric(intab.iloc[:,i], errors='coerce')
            # Gather list of NA row indicies
            NArows = intab.index[intab.iloc[:,i].astype(int) <= -99].tolist()
            # If there are null values, populate them with default values
            if len(NArows) > 0:
                intab.iloc[NArows,i] = pd.to_numeric(this_att_map.iloc[i,'DEF'], errors='coerce')
            intab.iloc[:,i] = intab.iloc[:,i].apply(lambda x: this_att_map['DEF'][i] if pd.isnull(x) else x)
            # Update valflag to True if there are null values
            for i, row in enumerate(intab.iloc[:,i]):
                if pd.isnull(row):
                    valflag[i] = True
                    
            self.write_log('.snitching on s.')
            for i in range(len(valflag)):
                if valflag[i]:
                    self.write_log(f"Invalid values of node attribute {this_att_map[i,'OUT']} found. Replace with value {this_att_map[i,'DEF']}")
            
            self.write_log('.finish s validation')

            return intab
            
    ####################
    # formatSurge()
    #	given a path to a surge shapefile,
    #	the shapefile will be read/loaded, with attributes formatted and validated
    # In:
    #	s_path = path to surge/wave datasets
    #   this_att_map = dataframe of SWEL data, loaded from the surge/wave datasets
    # Out:
    #	sp::SpatialPointsDataFrame of surge/wave dataset
    # called by:
    #	main()
    # calls:
    #	validateSurgeAttr2()
    #	haltscript()
    def formatSurge(self, s_path:str, this_att_map:pd.DataFrame) -> gpd.GeoDataFrame:
        self.write_log('.loading surge shapefile.')

        # Open shapefile, if that fails, kill script
        try:
            s_gdf = gpd.read_file(s_path)
        except Exception as e:
            self.write_log(f'Error loading node shapefile, {s_path}')
            self.write_log("Here's the original error message:")
            self.write_log(e)
            self.haltscript()
        
        self.write_log('.reformatting node table')
        # add unique surge ID
        s_gdf['SID'] = range(1, len(s_gdf)+1)
        
        # if incoming surge shape is Z-aware or M-aware,
        # then strip away all but the first two coordinate-columns
        s_gdf['geometry'] = s_gdf['geometry'].force_2d()
        s_tab = s_gdf.drop(columns=s_gdf.geometry.name)
        
        # find required attributes and make them if they dont exist
        for column in this_att_map.columns:
            if column not in s_tab.columns:
                s_tab[column] = pd.NA
        
        # filter and sort incoming attributes
        col_in_vals = this_att_map['IN'].tolist()
        s_tab = s_tab[col_in_vals]
        # map new attribute names
        col_out_vals = this_att_map['OUT'].tolist()
        s_tab.columns = col_out_vals
        
        self.write_log('.validating nodes.')
        try:
            s_tab = self.validateSurgeAttr2(s_tab, this_att_map)
        except Exception as e:
            self.write_log(f'Error validating shapefile, {s_path}')
            self.write_log("Here's the original error message:")
            self.write_log(e)
            print(e)
            self.haltscript()
            
        self.write_log('.packaging nodes.')
        
        return gpd.GeoDataFrame(s_tab, geometry=s_gdf.geometry, crs=s_gdf.geometry.crs)
    
    ####################
    # Calc_Nrp_AnnLoss4()
    #	Calculate Average Annualized Loss from N return periods
    #	Forumala adapted from HAZUS Technical Manual, 
    # in:
    #	in_losses = a Pandas Series of the losses ($) corresponding to,
    #	in_rpnames = a Pandas Series of return periods at which in_losses occur
    # out:
    #	Average Annualized Loss
    # called by:
    #	runMC_AALU_x4()
    # calls:
    #	NULL
    def Calc_Nrp_AnnLoss4(self, in_losses: pd.Series, in_rpnames: pd.Series) -> float:
        sel = in_rpnames.notna().to_list()
        in_losses = in_losses.iloc[sel]
        in_rpnames = in_rpnames.iloc[sel]
        
        sumAnnLoss = 0
        for i in range(in_losses.size):
            if i == in_losses.size-1:
                recur_2 = in_rpnames.iat[i]
                sumAnnLoss += (1/recur_2)*in_losses.iat[i]
            else:
                recur_1 = in_rpnames.iat[i]
                recur_2 = in_rpnames.iat[i+1]
                sumAnnLoss += ((1/recur_1)-(1/recur_2))*((in_losses.iat[i]+in_losses.iat[i+1])/2)
        return sumAnnLoss
    # Example,
    ## 
    # > rpvals = pd.Series([10, 25, 50, 100, 500])
    # > lossvals = pd.Series([0,0,79142,285939,436903])
    # > Calc_Nrp_AnnLoss4(lossvals, rpvals)
    ## [1] 6381.999
    
    #####################
    # getCurveByDDFid()
    # 	Given a DDF lookup table and a specific DDF id, the depth-damage curve values for that DDF will be returned
    # in:
    #	in_lut = DDF lookup table, columns = {BldgDmgFnID, m4, m3, m2, m1, p0, p1, p2, ..., p24}
    #	in_ddf = a DDF id
    # out:
    #	a Pandas Series representing % damage for depths (ft) relative to FFE (i.e. freeboard) = {-4ft, ..., +24ft}, 
    #		with index lables = depth (ft) relative to FFE
    #	if DDF does not exist, a Series of NA will be returned
    # called by:
    #	buildBldgFloodDepthTable6()
    # calls:
    #	removeNonNumeric()
    def getCurveByDDFid(self, in_lut: pd.DataFrame, in_ddf: int) -> pd.Series:
        sel = [in_lut.columns.get_loc(col) for col in in_lut.columns.to_list() if len(self.removeNonNumeric(col)) > 0]

        if in_lut["BldgDmgFnID"].isin([in_ddf]).any():
            ddf_row = in_lut.query(f"BldgDmgFnID == {in_ddf}")
            ddf_curve = ddf_row.iloc[0,min(sel):max(sel)+1].div(100)
        else:
            nan_data_dict = {in_lut.columns.to_list()[i]:np.nan for i in sel}
            ddf_curve = pd.Series(data={in_lut.columns.to_list()[i]:np.nan for i in sel}, index=list(nan_data_dict), name=None)
        
        repl_func = lambda x: "0" if x=="p0" else x.replace("p","+") if "p" in x else x.replace("m","-")
        ddf_curve.index = [repl_func(label) for label in in_lut.columns.take(sel).to_list()]
        return ddf_curve
    # Example,
    #> bldg_ddf_lut.head(2)
    ##  BldgDmgFnID Occupancy     Source                   F            Description m4 m3 m2 m1 p0 p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11 p12 p13 p14 p15 p16 p17 p18 p19 p20 p21 p22 p23 p24 Comment
    ##1         105      RES1        FIA one floor, no basement, Structure, A-Zone  0  0  0  0 18 22 25 28 30 31 40 43 43 45  46  47  47  49  50  50  50  51  51  52  52  53  53  54  54    NULL
    ##2         106      RES1 FIA (MOD.) one floor, w/ basement, Structure, A-Zone  7  7  7 11 17 21 29 34 38 43 50 50 54 55  55  57  58  60  62  63  65  67  69  70  72  74  76  77  79    NULL
    #> bldg_ddf = 105
    #> bldg_curve = getCurveByDDFid(bldg_ddf_lut,bldg_ddf)
    ##> bldg_curve
    ##  -4 -3 -2 -1    0    1    2    3   4    5   6    7    8    9   10   11   12   13  14  15  16   17   18   19   20   21   22   23   24
    ##1  0  0  0  0 0.18 0.22 0.25 0.28 0.3 0.31 0.4 0.43 0.43 0.45 0.46 0.47 0.47 0.49 0.5 0.5 0.5 0.51 0.51 0.52 0.52 0.53 0.53 0.54 0.54
    # ####################
    
    ####################
    # calcKernelDensity()
    # 	function to calculate the weighted kernel density 
    #	Inputs:
    #		NNtab = Pandas dataframe of nearby points within distance=bandwidth
    #			BID = point ID
    #			AAL = building AAL = the weight
    #			Dist = distance (feet) of building to cell centroid
    #		bw = bandwidth
    #	Outputs:
    #		weighted 2D kernel density calculation
    # 	https://desktop.arcgis.com/en/arcmap/latest/tools/spatial-analyst-toolbox/how-kernel-density-works.htm
    #	called by:
    #		main()
    #	calls:
    #		NULL
    def calcKernelDensity(self, NNtab:pd.DataFrame, bw:int) -> float:
        NNtab = NNtab.copy()
        NNtab.loc[:,'radius'] = bw
        in_sigma = NNtab.apply(lambda x: ((3/scipy.constants.pi)*x.iat[1]*(1-((x.iat[2]/x.iat[3])**2))**2), axis=1)
        sum_sigma = in_sigma.sum()
        out_val = (1/(bw**2))*sum_sigma
        return out_val
      
    # attachWSELtoBUILDING3()
    # 	function to find the 3 nearest surge points to a building point and adopt 
    # 	the mean average at each return period.  Replace -99999 (null) with NA before
    #	running mean, and then replace NaN after running mean with NA.  This will 
    #	compute averages without -99999 and insert NA where all input values are NULL
    # in:
    #	bldg_row = a row from a DataFrame of buildings dataset (from buildings GeoDataFrame with dropped geometry column)
    #   bldg_coord = numpy array of coordinates of the building (from buldings GeodataFrame.geometry.get_coordinates())
    #	surge_shp = GeoDataFrame of surge point dataset (inc geometry)
    #	in_attr_map = appropriate attribute map for SWEL or SWERR
    # out:
    #	mean surge values for all return periods for nearest surge points
    # called by:
    #	main()
    # calls:
    #	get_NNx()
    def attachWSELtoBUILDING3(self, bldg_row: pd.Series, bldg_coord: np.ndarray, surge_shp: gpd.GeoDataFrame,  in_attr_map: pd.DataFrame) -> pd.DataFrame:
        # unpack surge table and coordinates
        surge_tab = surge_shp.to_wkb().drop(columns=surge_shp.geometry.name)
        surge_coords = surge_shp.geometry.get_coordinates().to_numpy()
        bldg_coord_resize = np.resize(bldg_coord,(1,2))

        # find 3NN surge points to the building
        NN_res = self.get_NNx(surge_coords, bldg_coord_resize) 
        sid_func = lambda x, other: other["SID"].iat[x]
        NN_res["SID"] = NN_res["rowid"].apply(sid_func, args=(surge_tab,))

        # record the 3NN surge IDs
        row_prefix = pd.DataFrame.from_dict(data={"BID":[bldg_row.loc["BID"]],"DEMFT":[bldg_row.loc["DEMFT"]],"VALID":[0],"spt1":[NN_res.iat[0,2]],"spt2":[NN_res.iat[1,2]],"spt3":[NN_res.iat[2,2]]})

        # get the surge point rows identified above
        surge_res = surge_tab.iloc[surge_tab["SID"].isin(NN_res['SID'].to_list()).to_list(),:].copy()
        
        # swap -99999 for NA
        surge_res.mask(surge_res.eq(in_attr_map.iat[1,in_attr_map.columns.get_loc("DEF")]), pd.NA, inplace=True)
        
        # make a copy and plug NAs with lowest value in the row
        surge_resf = surge_res.copy()
        
        # swap surge.res with surge.resf to
        # get average of 3 surge points at each stage frequency, swapping NaN with NA
        # from the "fixed" results table
        surge_mean = surge_resf.iloc[:,in_attr_map.query("DDC == 1").index.to_list()].mean(axis=0, skipna=True, numeric_only=True)
        surge_mean.mask(surge_mean.isna(), pd.NA, inplace=True)
        
        # finally, use closest node to determine if nulls exist at building
        #   determine closest node from NN.res
        #if NAs exist in that node, transfer them to the same RP in surge.mean
        sel = surge_res.iloc[surge_res.eq(NN_res["SID"].iat[0]).any(axis=1).to_list(),:].isna().any()
        
        if sel.any():
            surge_mean.mask(sel, pd.NA, inplace=True)

        # fix the hiccups in surge.mean by lowering the offender to match the average of the bounding values
        surge_mean.index = list(range(surge_mean.size))
        diff_series = surge_mean.iloc[surge_mean.notna().to_list()].diff()
        if not diff_series.iloc[1:].ge(0).all():
            s_index_list = surge_mean.iloc[surge_mean.notna().to_list()].sort_index(ascending=False).index.to_list()[1:]
            for i in s_index_list:
                if surge_mean.at[i] > surge_mean.at[i+1]:
                    surge_mean.at[i] = surge_mean.at[i+1]
        
        # prep for merge and output
        row_suffix = surge_mean.apply(round, args=(3,))
        row_suffix.index = in_attr_map.query("DDC == 1")["OUT"].to_list()
        row_suffix = pd.DataFrame(data=row_suffix).T
        
        # create output row and add to table
        full_row = pd.concat([row_prefix,row_suffix], axis='columns')
        return full_row


    ####################
    # simulateDamageError6()
    #	function to simulate error on damage curve from 
    # In:
    #	intab = n(BFD) x 8 dataframe with columns for 
    #		Building flood depth
    #		Building flood depth error
    #		prob of wave height less than 1 ft
    #		prob of wave height between 1 and 3 feet
    #		prob of wave height greater or equal to 3 feet
    #		damage from DDF2
    #		damage from DDF3
    #		damage from DDF4
    # Out:
    #	 n(BFD) x 3 dataframe with columns for 
    #		min damage 
    #		best estimate damage
    #		max damage
    # called by:
    #	buildBldgFloodDepthTable6()
    # calls:
    #	NULL
    def simulateDamageError6(self, intab:pd.DataFrame) -> pd.DataFrame:
        
        BFDBound = pd.DataFrame({"LL": intab.iloc[:,0] - intab.iloc[:,1],"LU": intab.iloc[:,0] + intab.iloc[:,1]})
        Damage = (intab.iloc[:,2]*intab.iloc[:,5]) + (intab.iloc[:,3]*intab.iloc[:,6]) + (intab.iloc[:,4]*intab.iloc[:,7])
        
        # If there are more than 1 null value
        if int(intab.iloc[:,1].isna().sum()) > 1:

            y = Damage.values
            min_damage = np.nanmin(Damage)
            max_damage = np.nanmax(Damage)

            # lower bound:
            x_LL = intab.iloc[:,0].values
            xp_LL = BFDBound["LL"].values
            DamLL = np.interp(xp_LL,x_LL,y,left=np.nan,right=np.nan)
            DAMLL = pd.DataFrame({'LL':BFDBound.iloc[:,0],'Damage_LL':DamLL})
            mask_LL = DAMLL["LL"].notna() & DAMLL["Damage_LL"].isna()
            DAMLL.loc[mask_LL, "Damage_LL"] = min_damage
            
            # upper bound:
            x_LU = intab.iloc[:,0].values
            xp_LU = BFDBound["LU"].values
            DamLU = np.interp(xp_LU,x_LU,y,left=np.nan,right=np.nan)
            DAMLU = pd.DataFrame({'LU':BFDBound.iloc[:,1],'Damage_LU':DamLU})
            mask_LU = DAMLU["LU"].notna() & DAMLU["Damage_LU"].isna()
            DAMLU.loc[mask_LU, "Damage_LU"] = max_damage
                        
        else:
            # Select rows where they are not null
            sel = intab.iloc[:,1].notna()
            DAMLL = pd.DataFrame({'BFDBound':BFDBound.iloc[:,0],'Damage':Damage})
            DAMLL.iloc[sel,1] = 0
 
            DAMLU = pd.DataFrame({'BFDBound':BFDBound.iloc[:,0],'Damage':Damage})
        
        return pd.DataFrame({'DL':DAMLL.iloc[:,1],'DB':Damage,'DU':DAMLU.iloc[:,1]})
        
    
    ####################
    # buildSampledLoss2()
    # 	
    # in:
    #	FBtab0 = a buildings loss table
    #   pvals = N probabilistoc events 0..1
    # out:
    #	N x 5 dataframe with a row for each pval and columns for 
    #   pval, return period, Low curve value, best estimate curve value,
    #   high curve value 
    # called by:
    #	runMC_AALU_x4()
    # calls:
    #	NULL
    def buildSampledLoss2(self, FBtab0: pd.DataFrame, pvals: pd.DataFrame) -> pd.DataFrame:
        MC_prob = pd.to_numeric(pvals.iloc[:,0].sort_values(ascending=False))
        MC_rp = MC_prob.copy().apply(lambda x: 1/x)
        FBrp = FBtab0["RP"].copy()
        
        # make sure there are at least two RPs between 1 & 10k
        if FBrp.count() < 2:
            return pd.DataFrame(data={"MC_prob":[pd.NA], "MC_rp":[pd.NA], "MC_Lw":[0], "MC_Be":[0], "MC_Up":[0]})
        
        # initialize final loss = raw loss
        FBpLw = FBtab0["Loss_Lw"]
        FBpBe = FBtab0["Loss_BE"]
        FBpUp = FBtab0["Loss_Up"]
        
        # sample the loss curve
        if FBpBe.count() > 1:
            FBrp_log10 = np.log10(FBrp.to_numpy().flatten())
            FBrp_log10 = FBrp_log10[~np.isnan(FBrp_log10)]
            
            MCrp_log10 = np.log10(MC_rp.to_numpy())
            MCrp_log10 = MCrp_log10[~np.isnan(MCrp_log10)]

            MC_Lw = np.interp(x=MCrp_log10, xp=FBrp_log10, fp=FBpLw.to_numpy()[~np.isnan(FBpLw.to_numpy())], left=-999, right=-999)
            MC_Be = np.interp(x=MCrp_log10, xp=FBrp_log10, fp=FBpBe.to_numpy()[~np.isnan(FBpBe.to_numpy())], left=-999, right=-999)
            MC_Up = np.interp(x=MCrp_log10, xp=FBrp_log10, fp=FBpUp.to_numpy()[~np.isnan(FBpUp.to_numpy())], left=-999, right=-999)

            MC_Lw[MC_Lw==-999] = np.nan
            MC_Be[MC_Be==-999] = np.nan
            MC_Up[MC_Up==-999] = np.nan
        else:
            sel = FBtab0["RP"].notna().to_list()
            MC_prob = FBtab0["PVAL"].iloc[sel]
            MC_rp = FBtab0["RP"].iloc[sel]
            MC_Lw = FBpLw.iloc[sel]
            MC_Be = FBpBe.iloc[sel]
            MC_Up = FBpUp.iloc[sel]

        # create output table
        out_tab = pd.DataFrame(data={"MC_prob":MC_prob, "MC_rp":MC_rp, "MC_Lw":MC_Lw, "MC_Be":MC_Be, "MC_Up":MC_Up})
        out_tab.mask(out_tab.isna(), 0, inplace=True)
        return out_tab
    
    #####################
    # runMC_AALU_x4()
    #	Given a building , losses will be determined at flood depths in range of 
    #   -4 to +16, by 0.1 increments.  Loss uncertainty is estimated.
    #	This loss curve is then sampled N times
    #	and the AAL is calculated
    # in:
    #	in_tab = building DataFrame from PREP_SPDF
    #	pvals = Nx1 DataFrame with N probabilities, 0..1
    #	in_building = specific building BID to be evaluated
    #   inputs = object of 'Inputs' class
    # out:
    #  	1x4 dataframe with columns for 
    #		BID = building ID
    #		BAAL = best estimate building AAL
    #		BAALmin = minimum building AAL
    #		BAALmax = maximum building AAL
    # called by:
    #	main()
    # calls:
    # 	buildBldgFloodDepthTable6()
    #	adjust_Loss_DEDLIM1()
    #	buildSampledLoss2()
    # 	Calc_Nrp_AnnLoss4()
    def runMC_AALU_x4(self, in_tab: pd.DataFrame, pvals: pd.DataFrame, in_building: int, inputs, prep_atr_map: pd.DataFrame) -> pd.DataFrame:
        this_bldg_attr = in_tab[in_tab.BID==in_building]
        
        # Build the loss table by building flood depth
        bldg_ddf_df = pd.read_csv(inputs.bddf_lut_path)
        FBtab0 = self.buildBldgFloodDepthTable6(this_bldg_attr, inputs.use_waves, prep_atr_map, bldg_ddf_df)
        
        #check for truncated output
        if not np.any(FBtab0.columns.isin(["rLOSSLw"])):
            newFields = pd.Index(inputs.guts_attr_map["OUT"].to_list()).difference(FBtab0.columns)
            for F in newFields:
                FBtab0[F] = pd.NA
            FBtab0.columns = inputs.guts_attr_map["OUT"].to_list()
            FBtab0["DDFfam"] = this_bldg_attr.iloc[0, this_bldg_attr.columns.get_loc("DDF1")]
            FBtab0["BVAL"] = this_bldg_attr.iloc[0, this_bldg_attr.columns.get_loc("BLDG_VAL")]
            FBtab0["rLOSSLw"] = 0
            FBtab0["rLOSSBE"] = 0
            FBtab0["rLOSSUp"] = 0
        
        #####
        # make any adjustments to loss before annualizing
        FBtab0["Loss_Lw"] = FBtab0["rLOSSLw"]
        FBtab0["Loss_BE"] = FBtab0["rLOSSBE"]
        FBtab0["Loss_Up"] = FBtab0["rLOSSUp"]
        
        # adjust losses so that if DEM > (SWEL + 1sd), i.e. probability of ground being wet < 0.158655, 
        # then no damages, losses can occur
        # removes possibility of basements filling when ground is dry
        if inputs.use_eWet:
            sel = FBtab0.query("WET < 0.158655")
            if not sel.empty:
                FBtab0.loc[sel.index.to_list(), "Loss_Lw"] = 0
                FBtab0.loc[sel.index.to_list(), "Loss_BE"] = 0
                FBtab0.loc[sel.index.to_list(), "Loss_Up"] = 0
        
        # Adjust for Insurance delim and limit
        if inputs.use_insurance:
            # loss, deductible, limit
            ded = this_bldg_attr["BLDG_DED"]
            lim = this_bldg_attr["BLDG_LIM"]
            FBtab0["Loss_Lw"] = self.adjust_Loss_DEDLIM1(FBtab0["Loss_Lw"], ded, lim)
            FBtab0["Loss_BE"] = self.adjust_Loss_DEDLIM1(FBtab0["Loss_BE"], ded, lim)
            FBtab0["Loss_Up"] = self.adjust_Loss_DEDLIM1(FBtab0["Loss_Up"], ded, lim)
        
        # cutoff10
        if inputs.use_cutoff10:
            sel = FBtab0.query("RP < 10")
            FBtab0.loc[sel.index.to_list(), "Loss_Lw"] = 0
            FBtab0.loc[sel.index.to_list(), "Loss_BE"] = 0
            FBtab0.loc[sel.index.to_list(), "Loss_Up"] = 0
        # end adjustments
        #####
        
        # # write the table
        if inputs.use_outcsv:
            out_csv_dir = os.path.join(inputs.out_shp_path,"TAB")
            out_csv_name = f"BID_{'0'*(6-len(str(in_building)))}{in_building}.csv"
            FBtab0.to_csv(os.path.join(out_csv_dir,out_csv_name))
        
        # sample the loss curve probabilisticly
        MCLossTab = self.buildSampledLoss2(FBtab0, pvals)
        
        # edit 12/18/2024, need to check if 16ft flood depth represents an event
        #	that is higher freq than the lowest freq pval;
        # 	If so, then at least 1 pval is incorrectly being assigned 0 damages,
        #		and needs to be assigned the max known damage, instead.
        
        # edit 12/18/2024, need to check if the low freq pvals are
        #	w the range of probabilities in FBtab0, i.e. the 16ft event in FBtab0
        #	has a probability that is lower than the least probable pval.
        #	If the 16ft prob is > than some simulated events, those simulated events will be 
        #	assigned a damage value of 0, which is incorrect.  Instead we want to assign the max
        #	known damage to those simulated events.
        
        in_bldg_flag = 0
        # get the flood table last entry
        lastFBtab = FBtab0.tail(1)
        if FBtab0.notna().any().any() and pd.notna(lastFBtab.loc[:,"PVAL"]).all():
            # check if sampled loss tab has frequencies lower than the last entry
            #	if last entry is NA (normal) then nothing selected
            sel = MCLossTab.query(f"MC_prob < {lastFBtab.loc[:,'PVAL']}").index.to_list()
            # if there is a selection, then replace all the affected sampled loss tab entries
		    #	with max losses
            if len(sel) > 0:
                in_bldg_flag = 1
                # Get the Max Damage set
                max_dams = lastFBtab.loc[:,("Loss_Lw", "Loss_BE", "Loss_Up")]
                # insert
                MCLossTab.iloc[sel, MCLossTab.columns.get_indexer(("Loss_Lw", "Loss_BE", "Loss_Up"))] = max_dams
        # end edit 12/18/2024
        
        # if there are <2 loss values, then a curve cant be constructed. Loss = 0
        if MCLossTab.notna().query("MC_rp == True").shape[0] < 2:
            out_df = pd.DataFrame(data={"BID":in_building, "BAAL":0, "BAALmin":0, "BAALmax":0, "FLAG_DF16":in_bldg_flag}, index=[0])
        else:
            out_df = pd.DataFrame(data={"BID":in_building, 
                                           "BAAL":round(self.Calc_Nrp_AnnLoss4(MCLossTab["MC_Be"], MCLossTab["MC_rp"]),0),
                                           "BAALmin":round(self.Calc_Nrp_AnnLoss4(MCLossTab["MC_Lw"], MCLossTab["MC_rp"]),0),
                                           "BAALmax":round(self.Calc_Nrp_AnnLoss4(MCLossTab["MC_Up"], MCLossTab["MC_rp"]),0), 
                                           "FLAG_DF16":in_bldg_flag
                                          },
                                     index=[0]
                                    )
        return out_df

   
        
    
    ####################
    # buildBldgFloodDepthTable6()
    # 	function to 
    # in:
    #	this.attr.map = appropriate attribute map, for SWEL or TWL
    #	 use_waves = switch for wave use T/F
    #   prep_attr_map = the prep attribute map
    # out:
    #	mean surge values for all return periods for nearest surge points
    # called by:
    #	runMC_AALU_x4()
    # calls:
    #	removeNonNumeric()
    #	getZscore()
    #	getCurveByDDFid()
    #	simulateDamageError6()
    def buildBldgFloodDepthTable6(self, this_bldg_attr:pd.DataFrame, use_waves:bool, prep_attr_map:pd.DataFrame, bldg_ddf_lut:pd.DataFrame) -> pd.DataFrame:
        	
        # initialize zero error attributes
        DEMe = 0
        FFHe = 0
        
        # get building attributes from attribute table
        b_DEM = this_bldg_attr.iloc[0, this_bldg_attr.columns.get_loc(prep_attr_map.query("DESC=='ground elevation'")["OUT"].iat[0])]
        b_FFH = this_bldg_attr.iloc[0, this_bldg_attr.columns.get_loc(prep_attr_map.query("DESC=='first floor height'")["OUT"].iat[0])]
        b_VAL = this_bldg_attr.iloc[0, this_bldg_attr.columns.get_loc(prep_attr_map.query("DESC=='building value'")["OUT"].iat[0])]
        #b_DEM = this_bldg_attr.loc[0,prep_attr_map.loc[prep_attr_map["DESC"] == "ground elevation", "OUT"].iloc[0]]
        #b_FFH = this_bldg_attr.loc[0,prep_attr_map.loc[prep_attr_map["DESC"] == "first floor height", "OUT"].iloc[0]]
        #b_VAL = this_bldg_attr.loc[0,prep_attr_map.loc[prep_attr_map["DESC"] == "building value", "OUT"].iloc[0]]
        
        # get surge and surge errors attached to building
        b_SC = this_bldg_attr.iloc[0,this_bldg_attr.columns.get_indexer(prep_attr_map.query("DESC == 'surge elevation'")["OUT"].to_list())]
        b_SEC = this_bldg_attr.iloc[0,this_bldg_attr.columns.get_indexer(prep_attr_map.query("DESC == 'surge error'")["OUT"].to_list())]
        #b_SC = this_bldg_attr.loc[0,prep_attr_map.loc[prep_attr_map['DESC'] == 'surge elevation', 'OUT']]
        #b_SEC = this_bldg_attr.loc[0,prep_attr_map.loc[prep_attr_map["DESC"] == "surge error", "OUT"]]
        
        # get wave and wave errors attached to building
        if use_waves:
            b_WC = this_bldg_attr.iloc[0,this_bldg_attr.columns.get_indexer(prep_attr_map.query("DESC == 'wave height'")["OUT"].to_list())]
            b_WEC = this_bldg_attr.iloc[0,this_bldg_attr.columns.get_indexer(prep_attr_map.query("DESC == 'wave error'")["OUT"].to_list())]
            #b_WEC = this_bldg_attr.iloc[0,prep_attr_map.loc[prep_attr_map["DESC"] == "wave error", "OUT"]]
        else:
            b_WC = None
            b_WEC = None
        
        # extract RP from SWEL
        b_rpnames = [int(self.removeNonNumeric(i)) for i in b_SC.index.tolist()]
        
        # extract the SWEL, SWEL error, WAVE, and WAVE error values
        SWvals = b_SC.tolist()
        # SWEL 1 stddev
        SWerrs = b_SEC.tolist()
        
        if use_waves:
            WVvals = b_WC.tolist()
            
            WVerrs = b_WEC.tolist()
        else:
            WVvals = [0 for _ in range(len(SWvals))]
            WVerrs = WVvals

        # Build TWL values from SWEL and WAVEs
        TWLvals = [sw + (wv * 0.7) for sw, wv in zip(SWvals, WVvals)]
        # TWLerrs = np.sqrt(np.asarray(SWerrs, float)**2 + (np.asarray(WVerrs, float) * 0.7)**2)
        TWLerrs = [math.sqrt((sw**2) + ((wv*0.7)**2)) for sw, wv in zip(SWerrs, WVerrs)]

        
        # Create Table by Building Flood Depths
        FBvals = [round(x, 1) for x in [i / 10 for i in range(-40, 161)]]

        FBtab = pd.DataFrame({'BID':[this_bldg_attr['BID'].iat[0]]*len(FBvals),'BFD':FBvals})
        FBtab['DEM'] = np.round(b_DEM, 3)
        FBtab['FFE'] = np.round(b_FFH+b_DEM, 3)
        FBtab['FFEe']  = np.round(math.sqrt((FFHe**2)+(DEMe**2)), 3)
        FBtab['TWL'] = round((FBtab["BFD"] + FBtab["FFE"]), 3)
        
        # place holders for values to be calculated
        FBtab['TWLe'] = 0
        FBtab['BFDe'] = 0
        
        if ((FBtab['TWL'] >= min(TWLvals)) & (FBtab['TWL'] <= max(TWLvals))).sum() < 2:
            # There is not enough data in the table to continue
            # Less than two BFD@TWL values that intersect the range of TWL on the frequency curve
            # approx of the BFD@TWL will not be possible
            # Stop
            return FBtab
        
        interp = np.interp(x=FBtab['TWL'].values, xp=TWLvals, fp=np.log(b_rpnames), left=np.nan, right=np.nan)
        # Back-transform and round
        FBtab['RP'] = np.round(np.exp(interp), 3)
        FBtab['PVAL'] = 1/FBtab['RP']

        if FBtab['RP'].count() < 2:
            # There is not enough data in the table to continue
            # Less than two values of BFD have an RP on the curve
            # approx() will not be possible
            # Stop
            return FBtab
        
        interp = np.interp(x=np.log10(FBtab['RP'].values), xp=np.log10(b_rpnames), fp=TWLerrs, left=np.nan, right=np.nan)

        FBtab['TWLe'] = np.round(interp, 3)

	    #calc depth above FF error
        FBtab['BFDe'] = np.sqrt((FBtab['FFEe']**2)+(FBtab['TWLe']**2))
    
        interp = np.interp(x=np.log10(FBtab['RP'].values), xp=np.log10(b_rpnames), fp=SWvals)
        FBtab['SWEL'] = interp


        interp = np.interp(x=np.log10(FBtab['RP'].values), xp=np.log10(b_rpnames), fp=SWerrs)
        FBtab['SWELe'] = interp
        Z = self.getZscore(b_DEM, FBtab['SWEL'], FBtab['SWELe'])
        FBtab['WET'] = 1 - norm.cdf(Z)

        if use_waves:
            
            interp = np.interp(x=np.log10(FBtab['RP'].values), xp=np.log10(b_rpnames), fp=WVvals)
            FBtab['Hc'] = interp
            
            interp = np.interp(x=np.log10(FBtab['RP'].values), xp=np.log10(b_rpnames), fp=WVerrs)
            FBtab['Hce'] = interp

            Z = self.getZscore(1, FBtab['Hc'], FBtab['Hce'])
            FBtab['PWL1'] = norm.cdf(Z)
            FBtab['PW13'] = 0

            Z = self.getZscore(3, FBtab['Hc'], FBtab['Hce'])
            FBtab['PWG3'] = 1 - norm.cdf(Z)
            FBtab['PW13'] = (1 - FBtab['PWG3']) - FBtab['PWL1']
            
        else:
            FBtab['Hc'] = 0
            FBtab['Hce'] = 0
            FBtab['PWL1'] = 1
            FBtab['PW13'] = 0
            FBtab['PWG3'] = 0
            
        # get damages for each of the three assigned DDFs
        FBtab['DDFfam'] = this_bldg_attr['DDF1'].iat[0]
        dfnames = ["df" + str(int(v)) for v in this_bldg_attr.iloc[0, this_bldg_attr.columns.get_indexer(["DDF2", "DDF3", "DDF4"])].tolist()]
        temp = self.getCurveByDDFid(bldg_ddf_lut, int(this_bldg_attr['DDF2'].iat[0]))
        if temp.hasnans:
            self.write_log(f"Bad DDF assigned to BID {FBtab['BID'].iat[0]}. Setting damages to zero.")
            temp.fillna(0)

        interp = np.interp(x=FBtab['BFD'].values, xp=temp.index.astype(int).tolist(), fp=temp.values.astype(float), left=np.nan, right=np.nan)
        FBtab[dfnames[0]] = interp
        
        
        if use_waves:
            temp = self.getCurveByDDFid(bldg_ddf_lut, this_bldg_attr['DDF3'].iat[0])
            if temp.hasnans:
                self.write_log(f"Bad DDF assigned to BID {FBtab['BID'].iat[0]}. Setting damages to zero.")
                temp.fillna(0)

            interp = np.interp(x=FBtab['BFD'].values, xp=temp.index.astype(int).tolist(), fp=temp.values.astype(float), left=np.nan, right=np.nan)

            # Assign to the column named by the SECOND element of dfnames (index 1 in Python)
            FBtab[dfnames[1]] = interp
            
            temp = self.getCurveByDDFid(bldg_ddf_lut, this_bldg_attr['DDF4'].iat[0])
            if temp.hasnans:
                self.write_log(f"Bad DDF assigned to BID {FBtab['BID'].iat[0]}. Setting damages to zero.")
                temp.fillna(0)

            # Approx equivalent
            interp = np.interp(x=FBtab['BFD'].values, xp=temp.index.astype(int).tolist(), fp=temp.values.astype(float), left=np.nan, right=np.nan)

            # Assign using the THIRD element of dfnames
            FBtab[dfnames[2]] = interp

        else:
            FBtab[dfnames[1]] = 0
            FBtab[dfnames[2]] = 0
            
        temp = pd.DataFrame({'Hc':FBtab['Hc']})
        temp['Hc'].fillna(0)
        temp['ddf1'] = this_bldg_attr['DDF1'].iat[0] 
        temp['ddf2'] = this_bldg_attr['DDF2'].iat[0]
        temp['ddf3'] = this_bldg_attr['DDF3'].iat[0]
        temp['ddf4'] = this_bldg_attr['DDF4'].iat[0]
        
        # get simulated damage range (min, best estimate, max) from each curve
        DamCurve = self.simulateDamageError6(FBtab[["BFD","BFDe","PWL1","PW13","PWG3",f'df{temp['ddf2'][0]}',f'df{temp['ddf3'][0]}',f'df{temp['ddf4'][0]}']])
        
        FBtab['DAMLw'] = DamCurve['DL']
        FBtab['DAMPr'] = DamCurve['DB']
        FBtab['DAMUp'] = DamCurve['DU']
        
        FBtab['BVAL'] = b_VAL

        FBtab['rLOSSLw'] = (FBtab['DAMLw'] * FBtab['BVAL']).round(0)
        FBtab['rLOSSBE'] = (FBtab['DAMPr'] * FBtab['BVAL']).round(0)
        FBtab['rLOSSUp'] = (FBtab['DAMUp'] * FBtab['BVAL']).round(0)

        return FBtab         
    
    
    #####################
    # finalReportAAL2()
    #	format and print the AAL results to screen/log
    # in:
    #	results_tab = DataFrame of RESULTS.shp
    #   prep_attr_map = prep_attr_map DataFrame
    # out:
    #	NULL
    # called by:
    #	main()
    # calls:
    #	NULL
    def finalReportAAL2(self, results_tab=pd.DataFrame, prep_attr_map=pd.DataFrame) -> None:
        # summary statistics
        self.write_log(" ")
        self.write_log("Reporting AAL...")
        sel_col = prep_attr_map.query("DESC=='building value'").iat[0,prep_attr_map.columns.get_loc("OUT")]
        # Stats for all buildings in dataset
        self.write_log("* All Buildings *")
        self.write_log("Total Buildings:\t\t{0}".format(results_tab.shape[0]))
        self.write_log("Analyzed Buildings:\t\t{0}".format(int(results_tab.loc[:,"ANLYS"].sum(skipna=True))))
        self.write_log("Total Bldg AAL, Min Estimate:\t${:,}".format(int(round(pd.to_numeric(results_tab.loc[:,"BAALmin"]).sum(skipna=True),0))))
        self.write_log("Total Bldg AAL, Best Estimate:\t${:,}".format(int(round(pd.to_numeric(results_tab.loc[:,"BAAL"]).sum(skipna=True),0))))
        self.write_log("Total Bldg AAL, Max Estimate:\t${:,}".format(int(round(pd.to_numeric(results_tab.loc[:,"BAALmax"]).sum(skipna=True),0))))
        self.write_log("Total Building Exposure:\t${:,}".format(int(round(pd.to_numeric(results_tab.loc[:,sel_col]).sum(skipna=True),0))))
        
        # Stats on buildings that incurred loss
        self.write_log(" ")
        self.write_log("Min Estimate")
        sel = results_tab["BAALmin"].gt(0).to_list()
        self.write_log("\tBuildings:\t{0} Bldgs w/ AAL > 0".format(results_tab.iloc[sel,:].shape[0]))
        self.write_log("\tAAL:\t\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAALmin")].sum(skipna=True),0))))
        self.write_log("\tMean AAL:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAALmin")].mean(skipna=True),0))))
        self.write_log("\tExposure:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].sum(skipna=True),0))))
        self.write_log("\tMean Exp:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].mean(skipna=True),0))))
        
        self.write_log(" ")
        self.write_log("Best Estimate")
        sel = results_tab["BAAL"].gt(0).to_list()
        self.write_log("\tBuildings:\t{0} Bldgs w/ AAL > 0".format(results_tab.iloc[sel,:].shape[0]))
        self.write_log("\tAAL:\t\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAAL")].sum(skipna=True),0))))
        self.write_log("\tMean AAL:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAAL")].mean(skipna=True),0))))
        self.write_log("\tExposure:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].sum(skipna=True),0))))
        self.write_log("\tMean Exp:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].mean(skipna=True),0))))
        
        self.write_log(" ")
        self.write_log("Max Estimate")
        sel = results_tab["BAALmax"].gt(0).to_list()
        self.write_log("\tBuildings:\t{0} Bldgs w/ AAL > 0".format(results_tab.iloc[sel,:].shape[0]))
        self.write_log("\tAAL:\t\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAALmax")].sum(skipna=True),0))))
        self.write_log("\tMean AAL:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc("BAALmax")].mean(skipna=True),0))))
        self.write_log("\tExposure:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].sum(skipna=True),0))))
        self.write_log("\tMean Exp:\t${:,}".format(int(round(results_tab.iloc[sel, results_tab.columns.get_loc(sel_col)].mean(skipna=True),0))))
