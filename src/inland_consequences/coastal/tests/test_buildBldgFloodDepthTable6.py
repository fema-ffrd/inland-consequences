import os
import sys

# Get the path of the current directory's parent
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add the parent directory to the system path
sys.path.append(parent_dir)

from _pfracoastal_lib import _PFRACoastal_Lib
import pandas as pd
from os import path

working_dir = path.abspath(path.dirname(__file__))

def test_buildBldgFloodDepthTable6():
    lib = _PFRACoastal_Lib()
    
    csv_dict = {
        '1':{
            'Input': {
                'prep_attr_map':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_prep_attr_map_INPUT_1.csv"), float_precision='round_trip'),
                'this_bldg_attr':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_this_bldg_attr_INPUT_1.csv"), float_precision='round_trip'),
                'bldg_ddf_lut':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_bldg_ddf_lut_INPUT_1.csv"), float_precision='round_trip')
            },
            'Output': {
                'out_tab':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/buildBldgFloodDepthTable6_OUTPUT_1.csv"), float_precision='round_trip')
            }
        },
        '3':{
            'Input': {
                'prep_attr_map':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_prep_attr_map_INPUT_3.csv"), float_precision='round_trip'),
                'this_bldg_attr':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_this_bldg_attr_INPUT_3.csv"), float_precision='round_trip'),
                'bldg_ddf_lut':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/buildBldgFloodDepthTable6_bldg_ddf_lut_INPUT_3.csv"), float_precision='round_trip')
            },
            'Output':{
                'out_tab':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/buildBldgFloodDepthTable6_OUTPUT_3.csv"), float_precision='round_trip')
            }
        }
    }
    for run_type in csv_dict:
        
        df_equal = True
        
        prep_attr_map = csv_dict[run_type]['Input']['prep_attr_map']
        this_bldg_attr = csv_dict[run_type]['Input']['this_bldg_attr']
        bldg_ddf_lut = csv_dict[run_type]['Input']['bldg_ddf_lut']
        out_tab = csv_dict[run_type]['Output']['out_tab']
        
        ret = lib.buildBldgFloodDepthTable6(this_bldg_attr,True,prep_attr_map,bldg_ddf_lut)
        
        ret_rnd = ret.round(7)
        out_tab_rnd = out_tab.round(7)

        # First check shape
        if ret_rnd.shape != out_tab_rnd.shape:
            df_equal = False
        
        # Check row/column labels match
        if not (ret_rnd.index.equals(out_tab_rnd.index) and ret_rnd.columns.equals(out_tab_rnd.columns)):
            df_equal = False

        # Iterate over rows and columns
        for row in ret_rnd.index:
            for col in ret_rnd.columns:
                v1 = ret_rnd.at[row, col]
                v2 = out_tab_rnd.at[row, col]

                # Treat NaN == NaN as equal
                if pd.isna(v1) and pd.isna(v2):
                    continue

                if v1 != v2:
                    df_equal = False


        assert df_equal
