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
    def padTrailingSpaces(inText: str, tLength=0) -> str:
        l = len(inText)
        if l >= tLength:
            outText = inText
        else:
            outText = ''.join([inText, (tLength - l)*' '])
        return outText