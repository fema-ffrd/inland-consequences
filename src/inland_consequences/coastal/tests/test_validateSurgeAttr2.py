#####NOTE: The test for validateSurgeAttr2 is included in this test as the formatSurge function is the only function that calls validateSurgeAttr2#####

import os
import sys
import pytest
import numpy as np

# Get the path of the current directory's parent
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add the parent directory to the system path
sys.path.append(parent_dir)

from _pfracoastal_lib import _PFRACoastal_Lib
import pandas as pd
from os import path
import geopandas as gpd

working_dir = path.abspath(path.dirname(__file__))

@pytest.fixture
def get_comparison_data(run_type:str) -> dict:
    # Gathers input data sources for the run type
    src_data_dict = {
        'surgeA':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/validateSurgeAttr2_surgeA_results.csv"), float_precision='round_trip'),
        'surgeB':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/validateSurgeAttr2_surgeB_results.csv"), float_precision='round_trip'),
        'waveA':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/validateSurgeAttr2_waveA_results.csv"), float_precision='round_trip'),
        'waveB':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/validateSurgeAttr2_waveB_results.csv"), float_precision='round_trip'),
    }

    src_dbf_path = {
        'surgeA':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.dbf"),
        'surgeB':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_84_sample.dbf"),
        'waveA':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_BE_sample.dbf"),
        'waveB':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_84_sample.dbf")
    }
    
    src_shp_path = {
        'surgeA':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.shp"),
        'surgeB':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_84_sample.shp"),
        'waveA':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_BE_sample.shp"),
        'waveB':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_84_sample.shp")
    }

    return {
        'target_df':src_data_dict[run_type],
        'dbf':src_dbf_path[run_type],
        'shp':src_shp_path[run_type]
    }

def test_validateSurgeAttr2():
    lib = _PFRACoastal_Lib()
    for run_type in ['surgeA','surgeB','waveA','waveB']:

        run_data = get_comparison_data(run_type)

        # create extensible swel attribute map
        temp_tab = gpd.read_file(run_data['shp'], ignore_geometry=True)

        #get all names that begin with 'e'
        temp_cols = [col for col in temp_tab.columns.to_list() if col[0]=='e']

        #get the numeric portion of those columns
        rp_avail = [lib.removeNonNumeric(col) for col in temp_cols]

        # add these to the attribute map
        attr_dict = {
            "IN":["SID"]+temp_cols,
            "OUT":["SID"]+[run_type[:1]+col for col in rp_avail],
            "DESC":["node id"]+["surge elevation" for i in range(len(temp_cols))],
            "TYPE":['int32' for i in range(len(["SID"]+temp_cols))],
            "DEF":[-99999 for i in range(len(["SID"] + temp_cols))],
            "CHECK":[0]+[1 for i in range(len(temp_cols))],
            "DDC":[0]+[1 for i in range(len(temp_cols))]
        }
        attr_map = pd.DataFrame(attr_dict)

        s_tab = gpd.read_file(run_data['dbf'])

        # add unique surge ID
        s_tab['SID'] = range(1, len(s_tab)+1)
        
        # if incoming surge shape is Z-aware or M-aware,
        # then strip away all but the first two coordinate-columns
        s_tab['geometry'] = s_tab['geometry'].force_2d()
        
        # find required attributes and make them if they dont exist
        for column in attr_map.columns:
            if column not in s_tab.columns:
                s_tab[column] = pd.NA
        
        # filter and sort incoming attributes
        col_in_vals = attr_map['IN'].tolist()
        s_tab = s_tab[col_in_vals]
        # map new attribute names
        col_out_vals = attr_map['OUT'].tolist()
        s_tab.columns = col_out_vals
        
        ret = lib.validateSurgeAttr2(run_data['target_df'], attr_map)

        assert ret.equals(run_data['target_df'])
