import os
import sys
import pytest

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
def get_comparison_data() -> dict:
    
    src_data_dict = {
        'src_data': {
            'surgeA':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/formatSurge_surgeA_results.csv"), float_precision='round_trip'),
            'surgeB':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/formatSurge_surgeB_results.csv"), float_precision='round_trip'),
            'waveA':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/formatSurge_waveA_results.csv"), float_precision='round_trip'),
            'waveB':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/formatSurge_waveB_results.csv"), float_precision='round_trip'),
        },
        'dbf_path':{
            'surgeA':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.dbf"),
            'surgeB':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_84_sample.dbf"),
            'waveA':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_BE_sample.dbf"),
            'waveB':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_84_sample.dbf")
        },
        'shp_path':{
            'surgeA':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.shp"),
            'surgeB':path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_84_sample.shp"),
            'waveA':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_BE_sample.shp"),
            'waveB':path.join(working_dir,"_data/TEST_CALC/input/Calc_Hc_84_sample.shp")
        }
    }
    
    return src_data_dict


def test_formatSurge(get_comparison_data):
    lib = _PFRACoastal_Lib()
    for run_type in ['surgeA','surgeB','waveA','waveB']:

        run_data = get_comparison_data

        # create extensible swel attribute map
        temp_tab = gpd.read_file(run_data['shp_path'][run_type], ignore_geometry=True)

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
        ret = lib.formatSurge(run_data['dbf_path'][run_type], attr_map)

        assert ret.equals(run_data['src_data'][run_type])
