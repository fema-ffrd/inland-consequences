import rasterio
import geopandas as gpd
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
    # validateBuildingAttr()
    #	function to test the attribute table of a building dataset in order 
    #	to determine if 
    #		the required fields exist,
    #		the fields contain the correct type (numeric vs character) of data
    #		field contains valid data
    #	If required fields are missing, they will be created an populated with default value
    #	If required fields contain unexpected values (inc NULLS), they will be replaced by the default
    #	*The table bldg.attr.map contains the information about required field names, domains, and defaults
    # In:
    #	intab = attribute table from building dataset
    # Out:
    #	validated building attribute table 
    # called by:
    #	formatBuildings()
    # calls:
    #	NULL
    def validateBuildingAttr(self, inputs: Inputs, intab: pd.DataFrame) -> pd.DataFrame:
        self.write_log(".start b validation.")
        
        # initialize attribute error flags as FALSE
        val_flag = [False for i in range(inputs.bldg_attr_map.shape[0])]
        
        self.write_log(".casting numeric fields.")
        # Replace non-numeric values for numeric-type attributes with the default value
        sel = inputs.bldg_attr_map.query("TYPE == 'int32' and CHECK == 1").index.to_list()
        for i in sel:
            intab.iloc[:,i] = intab.iloc[:,i].astype('int32')
            self.write_log(f".Check {inputs.bldg_attr_map.at[i,"IN"]}."))
            
            pre_mask_col = intab.iloc[:,i]
            intab.iloc[:,i].mask(intab.iloc[:,i].isna(), inputs.bldg_attr_map["DEF"].astype(inputs.bldg_attr_map.at[i,"TYPE"]).at[i], inplace=True)
            post_mask_col = intab.iloc[:,i]
            
            if pre_mask_col.ne(post_mask_col, fill_value=-8888): # fill value here is arbitrary, just can't be a default value
                val_flag[i] = True
        
        self.write_log(".checking domained fields.")
        # Fix Domained Variables
        sel = inputs.bldg_attr_map.query("pd.notna(DOM)==True").index.to_list()
        for i in sel:
            self.write_log(f".Check {inputs.bldg_attr_map.at[i,"IN"]}."))
            pre_where_col = intab.iloc[:,i]
            intab.iloc[:,i].where(intab.iloc[:,i].isin(list(inputs.bldg_attr_map.at[i,"DOM"])), inputs.bldg_attr_map["DEF"].astype(inputs.bldg_attr_map.at[i,"TYPE"]).at[i], inplace=True)
            post_where_col = intab.iloc[:,i]
            
            if pre_where_col.ne(post_where_col, fill_value=-8888): # fill value here is arbitrary, just can't be a default value
                val_flag[i] = True
        
        bsmt_finish_type_index = inputs.bldg_attr_map.query("DESC == 'basement finish type'").index[0]
        fndn_type_index = inputs.bldg_attr_map.query("DESC == 'foundation type'").index[0]
        # check if basements have non basement finishes
        sel = intab.query(f"{intab.columns[bsmt_finish_type_index]} == 0 and {intab.columns[fndn_type_index]} == 2").index.to_list()
        if len(sel) > 0:
            self.write_log(f"Warning. {len(sel)} instances of foundation type 2 incorrectly paired with basement finish type 0. Substituting basement finish type 1.")
            intab.iloc[sel,bsmt_finish_type_index] = 1
        
        # check if non-basements have basement finishes
        sel = intab.query(f"{intab.columns[bsmt_finish_type_index]} != 0 and {intab.columns[fndn_type_index]} != 2").index.to_list()
        if len(sel) > 0:
            self.write_log(f"Warning. {len(sel)} instances of basement finish types 1,2 incorrectly paired with foundation type other than 2. Substituting basement finish type 0.")
            intab.iloc[sel,bsmt_finish_type_index] = 0
        
        # report valflags
        self.write_log(".snitching on b.")
        for i in range(len(val_flag)):
            if val_flag[i]:
                self.write_log(f"Invalid values of building attribute {inputs.bldg_attr_map.at[i,"IN"]} found. Replaced with value {inputs.bldg_attr_map.loc[i,"DEF"]}")
        
        self.write_log(".finish b validation.")
        return intab