import rasterio
import geopandas as gpd
import scipy
import logging
import typing
import multiprocessing
import os

class _PFRACoastal_Lib:
    def __init__(self) -> object:
        pass
    
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
    def getZscore(x: float, mean_data: float, sd_data: float) -> float:
        return (x - mean_data) / sd_data