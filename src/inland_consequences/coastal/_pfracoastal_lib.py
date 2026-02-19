import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
import os
import csv
from re import sub
import sys

logger = logging.getLogger(__name__)

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
    ##  BldgDmgFnID Occupancy     Source                               Description m4 m3 m2 m1 p0 p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11 p12 p13 p14 p15 p16 p17 p18 p19 p20 p21 p22 p23 p24 Comment
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
        MC_prob = pvals.iloc[:,0].sort_values(ascending=False)
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