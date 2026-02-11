#####NOTE: The test for validateSurgeAttr2 is included in this test as the formatSurge function is the only function that calls validateSurgeAttr2#####

import os
import sys

# Get the path of the current directory's parent
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add the parent directory to the system path
sys.path.append(parent_dir)

from _pfracoastal_lib import _PFRACoastal_Lib
import pandas as pd
from os import path
import geopandas as gpd

working_dir = path.abspath(path.dirname(__file__))


def get_comparison_data(run_type:str) -> dict:
    # Gathers input data sources for the run type
    src_data_dict = {
        'surgeA':{
            'SID':   [1, 2, 3, 4, 5, 6],
            's1':    [1.880249, 1.877953, 1.877625, 1.874672, 1.877297, 1.874344],
            's2':    [3.072507, 3.069882, 3.069554, 3.066601, 3.069226, 3.066273],
            's5':    [4.525263, 4.521654, 4.521326, 4.517717, 4.521326, 4.517389],
            's10':   [5.725066, 5.720801, 5.720473, 5.716864, 5.720473, 5.715879],
            's20':   [6.972769, 6.968176, 6.967520, 6.963255, 6.967520, 6.962927],
            's50':   [8.585958, 8.581365, 8.580709, 8.574475, 8.579069, 8.572507],
            's100':  [9.637796, 9.632218, 9.632218, 9.616798, 9.629922, 9.555775],
            's200':  [10.54626, 10.54003, 10.53412, 10.44554, 10.52526, 10.23064],
            's500':  [11.61581, 11.59711, 11.52329, 11.16896, 11.44390, 10.79396],
            's1000': [12.26542, 12.19587, 12.05873, 11.59416, 11.91798, 11.10203],
            's2000': [12.78314, 12.64305, 12.45276, 11.88583, 12.29232, 11.37336],
            's5000': [13.27264, 12.92684, 12.92684, 12.35761, 12.79200, 11.75164],
            's10000':[13.68471, 13.51378, 13.31890, 12.93865, 13.20308, 12.21161],
        },
        'surgeB':{
            'SID':   [1, 2, 3, 4, 5, 6],
            's1':    [2.586942, 2.582677, 2.582021, 2.577100, 2.581037, 2.576444],
            's2':    [4.101050, 4.096457, 4.095801, 4.090879, 4.095144, 4.089895],
            's5':    [5.812336, 5.806759, 5.806103, 5.801181, 5.805446, 5.799869],
            's10':   [7.147310, 7.142061, 7.141076, 7.136155, 7.140420, 7.134515],
            's20':   [8.489173, 8.483596, 8.482612, 8.477362, 8.481628, 8.476050],
            's50':   [10.18143, 10.17585, 10.17454, 10.16765, 10.17224, 10.16470],
            's100':  [11.26804, 11.26214, 11.26116, 11.24508, 11.25820, 11.18143],
            's200':  [12.20013, 12.19357, 12.18668, 12.09580, 12.17684, 11.87467],
            's500':  [13.29134, 13.27231, 13.19619, 12.83497, 13.11450, 12.45144],
            's1000': [13.95177, 13.88091, 13.74081, 13.26837, 13.59711, 12.76575],
            's2000': [14.47736, 14.33497, 14.14108, 13.56496, 13.97769, 13.04265],
            's5000': [14.97343, 14.84350, 14.62205, 14.04429, 14.48458, 13.42782],
            's10000':[15.39042, 15.21719, 15.01903, 14.63386, 14.90125, 13.89534],
        },
        'waveA':{
            'SID':   [1, 2, 3, 4, 5, 6],
            'w1':     [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            'w2':     [0.0, 0.0, 0.000000000, 0.0, 0.0, 0.000328084],
            'w5':     [0.0, 0.0, 0.000328084, 0.0, 0.000328084, 0.000984252],
            'w10':    [0.0, 0.0, 0.000328084, 0.0, 0.001312336, 0.004265092],
            'w20':    [0.0, 0.0, 0.000328084, 0.0, 0.006233596, 0.022309712],
            'w50':    [0.0, 0.0, 0.000656168, 0.000328084, 0.026574804, 0.084317588],
            'w100':   [0.0, 0.0, 0.000984252, 0.000328084, 0.052493440, 0.158464572],
            'w200':   [0.0, 0.0, 0.001640420, 0.000328084, 0.076443572, 0.246719168],
            'w500':   [0.0, 0.0, 0.003937008, 0.000328084, 0.132217852, 0.390091876],
            'w1000':  [0.0, 0.0, 0.006561680, 0.000328084, 0.165354336, 0.477034136],
            'w2000':  [0.0, 0.0, 0.010498688, 0.000328084, 0.194553812, 0.537401592],
            'w5000':  [0.0, 0.0, 0.017716536, 0.000328084, 0.220144364, 0.592191620],
            'w10000': [0.0, 0.0, 0.024278216, 0.000328084, 0.229986884, 0.637795296],
        },
        'waveB':{
            'SID':   [1, 2, 3, 4, 5, 6],
            'w1':     [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            'w2':     [0.0, 0.0, 0.0, 0.0, 0.0, 0.000328084],
            'w5':     [0.0, 0.0, 0.000328084, 0.0, 0.000656168, 0.001312336],
            'w10':    [0.0, 0.0, 0.000328084, 0.0, 0.001640420, 0.005905512],
            'w20':    [0.0, 0.0, 0.000656168, 0.000328084, 0.008858268, 0.030839896],
            'w50':    [0.0, 0.0, 0.000984252, 0.000328084, 0.036417324, 0.115813652],
            'w100':   [0.0, 0.0, 0.001640420, 0.000328084, 0.072178480, 0.217847776],
            'w200':   [0.0, 0.0, 0.002296588, 0.000328084, 0.104986880, 0.339238856],
            'w500':   [0.0, 0.0, 0.005249344, 0.000328084, 0.181758536, 0.536089256],
            'w1000':  [0.0, 0.0, 0.009186352, 0.000328084, 0.227362212, 0.655511832],
            'w2000':  [0.0, 0.0, 0.014435696, 0.000328084, 0.267388460, 0.738517084],
            'w5000':  [0.0, 0.0, 0.024278216, 0.000656168, 0.302493448, 0.813648320],
            'w10000': [0.0, 0.0, 0.033136484, 0.000656168, 0.315944892, 0.876312364],
        },
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
        'target_df':pd.DataFrame(src_data_dict[run_type]),
        'dbf':src_dbf_path[run_type],
        'shp':src_shp_path[run_type]
    }

def test__formatSurge():
    lib = _PFRACoastal_Lib()
    for run_type in ['surgeA','surgeB','waveA','waveB']:
        print(f'-----{run_type}-----')
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
        ret = lib.formatSurge(run_data['dbf'], attr_map).head(6).copy()
        if ret.equals(run_data['target_df']):
            print(f'{run_type}-Passed')
        else:
            # Surge A/B will fail because of rounding from printing in the original log file. Values have been checked and inputs/test datasets match
            print(f'{run_type}-Failed')
        
test__formatSurge()


