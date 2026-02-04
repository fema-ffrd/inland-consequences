import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
import os
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
        nn_res['rowid'] = list(range(1, nn_dist.shape[0]+1))
        
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
