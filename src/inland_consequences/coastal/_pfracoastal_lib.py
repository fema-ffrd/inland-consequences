import rasterio
import geopandas as gpd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
import os
from re import sub

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
    def adjust_Loss_DEDLIM1(loss: int, ded=0, lim=100_000_000) -> int:
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