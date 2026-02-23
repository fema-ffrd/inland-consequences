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

def test_simulateDamageError6():
    lib = _PFRACoastal_Lib()
    
    csv_dict = {
        'Input_CSV': {
            'in_tab':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/input/simulateDamageError6_INPUT.csv"), float_precision='round_trip')
        },
        'Output_CSV':{
            'out_tab':pd.read_csv(path.join(working_dir,"_data/TEST_CALC/output/simulateDamageError6_OUTPUT.csv"), float_precision='round_trip')

        }
    }
    
    ret = lib.simulateDamageError6(csv_dict['Input_CSV']['in_tab'])

    assert ret.equals(csv_dict['Output_CSV']['out_tab'])
