from inland_consequences.coastal import _pfracoastal_lib
import pandas as pd
import pytest
import numpy as np
from os import path

lib = _pfracoastal_lib._PFRACoastal_Lib()


@pytest.fixture
def test_data():
    root_dir = path.abspath(path.dirname(__file__))
    ddf_lut_csv = path.join(root_dir, "_data", "Building_DDF_LUT_CPFRAworking.csv")
    ddf_lut_df = pd.read_csv(ddf_lut_csv)

    results_df = ddf_lut_df.iloc[:,2:].div(100)
    nan_data_df = pd.DataFrame({col:[np.nan] for col in results_df.columns.to_list()})
    results_df = pd.concat([results_df, nan_data_df])

    repl_func = lambda x: "0" if x=="p0" else x.replace("p","+") if "p" in x else x.replace("m","-")
    rename_map = {col:repl_func(col) for col in results_df.columns.to_list()}
    results_df.rename(columns=rename_map, inplace=True)

    return (ddf_lut_df, results_df)

def test_ddf_1900_curve(test_data, lib=lib):
    ddf_id = 1900
    ddf_lut, results_df = test_data
    correct_output = results_df.iloc[0]
    ret = lib.getCurveByDDFid(in_lut=ddf_lut, in_ddf=ddf_id)
    assert ret.eq(correct_output).all()

def test_nan_row_output(test_data, lib=lib):
    ddf_id = 9999
    ddf_lut, results_df = test_data
    correct_output = results_df.iloc[-1]
    correct_output.name = None
    ret = lib.getCurveByDDFid(in_lut=ddf_lut, in_ddf=ddf_id)
    val_chk = ret.isna().all() and correct_output.isna().all()
    index_chk = ret.index.identical(correct_output.index)
    assert val_chk and index_chk
    