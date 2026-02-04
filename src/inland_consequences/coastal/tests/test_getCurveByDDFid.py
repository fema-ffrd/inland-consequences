from inland_consequences.coastal import _pfracoastal_lib
import pandas as pd
import pytest
import numpy as np

lib = _pfracoastal_lib._PFRACoastal_Lib()

@pytest.fixture
def test_data():
    test_ddf_lut_dict = {
        "BldgDmgFnID":[105,106],
        "Occupancy":["RES1","RES1"],
        "Source":["FIA","FIA (MOD.)"],
        "Description":["one floor, no basement, Structure, A-Zone", "one floor, w/ basement, Structure, A-Zone"],
        "m4":[0,7],
        "m3":[0,7],
        "m2":[0,7],
        "m1":[0,11],
        "p0":[18,17],
        "p1":[22,21],
        "p2":[25,29],
        "p3":[28,34],
        "p4":[30,38],
        "p5":[31,43],
        "p6":[40,50],
        "p7":[43,50],
        "p8":[43,54],
        "p9":[45,55],
        "p10":[46,55],
        "p11":[47,57],
        "p12":[47,58],
        "p13":[49,60],
        "p14":[50,62],
        "p15":[50,63],
        "p16":[50,65],
        "p17":[51,67],
        "p18":[51,69],
        "p19":[52,70],
        "p20":[52,72],
        "p21":[53,74],
        "p22":[53,76],
        "p23":[54,77],
        "p24":[54,79],
        "Comment":[None,None]
    }
    ddf_lut_df = pd.DataFrame.from_dict(test_ddf_lut_dict)

    results_dict = {
        "-4":[0,.07,np.nan],
        "-3":[0,.07,np.nan],
        "-2":[0,.07,np.nan],
        "-1":[0,0.11,np.nan],
        "0":[0.18,0.17,np.nan],
        "+1":[0.22,0.21,np.nan],
        "+2":[0.25,0.29,np.nan],
        "+3":[0.28,0.34,np.nan],
        "+4":[0.30,0.38,np.nan],
        "+5":[0.31,0.43,np.nan],
        "+6":[0.40,0.50,np.nan],
        "+7":[0.43,0.50,np.nan],
        "+8":[0.43,0.54,np.nan],
        "+9":[0.45,0.55,np.nan],
        "+10":[0.46,0.55,np.nan],
        "+11":[0.47,0.57,np.nan],
        "+12":[0.47,0.58,np.nan],
        "+13":[0.49,0.60,np.nan],
        "+14":[0.50,0.62,np.nan],
        "+15":[0.50,0.63,np.nan],
        "+16":[0.50,0.65,np.nan],
        "+17":[0.51,0.67,np.nan],
        "+18":[0.51,0.69,np.nan],
        "+19":[0.52,0.70,np.nan],
        "+20":[0.52,0.72,np.nan],
        "+21":[0.53,0.74,np.nan],
        "+22":[0.53,0.76,np.nan],
        "+23":[0.54,0.77,np.nan],
        "+24":[0.54,0.79,np.nan]
    }
    results_df = pd.DataFrame.from_dict(results_dict)
    ret_tup = (ddf_lut_df, results_df)
    return (ddf_lut_df, results_df)

def test_ddf_105_curve(test_data, lib=lib):
    ddf_id = "105"
    ddf_lut, results_df = test_data
    correct_output = results_df.iloc[0]
    ret = lib.getCurveByDDFid(in_lut=ddf_lut, in_ddf=ddf_id)
    assert ret.eq(correct_output).all()

def test_ddf_106_curve(test_data, lib=lib):
    ddf_id = "106"
    ddf_lut, results_df = test_data
    correct_output = results_df.iloc[1]
    ret = lib.getCurveByDDFid(in_lut=ddf_lut, in_ddf=ddf_id)
    assert ret.eq(correct_output).all()

def test_nan_row_output(test_data, lib=lib):
    ddf_id = "2903"
    ddf_lut, results_df = test_data
    correct_output = results_df.iloc[2]
    correct_output.name = None
    ret = lib.getCurveByDDFid(in_lut=ddf_lut, in_ddf=ddf_id)
    val_chk = ret.isna().all() and correct_output.isna().all()
    index_chk = ret.index.identical(correct_output.index)
    assert val_chk and index_chk
    