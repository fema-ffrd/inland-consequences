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
        
        # determine 1st digit
        calc_digit1 = lambda x: 1 if x==1 else 2
        digit1 = calc_digit1(numStor)
        
        # determine 2nd digit
        calc_digit2 = lambda x: 9 if x==9 else 2 if x==2 else 4
        digit2 = calc_digit2(fndtn)
        
        # determine 3rd digit
        calc_digit3 = lambda x,y: 1 if x==2 and y==0 else x if x==2 and y!=0 else 0
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