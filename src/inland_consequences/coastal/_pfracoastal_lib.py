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
        b_tab.loc[:,"BID"] = list(range(1,b_tab.shape[0]+1))
        
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