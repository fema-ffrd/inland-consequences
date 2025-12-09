import rasterio
import geopandas as gpd
import scipy
import logging
import typing
import multiprocessing
import os
from re import sub

class _PFRACoastal_Lib:
    def __init__(self) -> object:
        pass
    
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
    def removeNonNumeric(inText: str) -> str:
        outText = sub("[^0-9.-]", "", inText)
        return outText