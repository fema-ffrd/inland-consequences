from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd
import pandas as pd
import pytest

@pytest.fixture
def get_test_data():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    root_dir = path.abspath(path.dirname(__file__))
    test_dir = path.join(root_dir, "_data","TEST_CALC","output")
    inputs_obj = pfracoastal.Inputs()

    prep_shp_path = path.join(test_dir, "Test1_PREP.shp")
    pvals_csv_path = path.join(test_dir, "pvals.csv")
    buildings_shp_path = path.join(test_dir, "Test1_BUILDINGS.shp")
    results_shp_path = path.join(test_dir, "Test1_RESULTS.shp")

    prep_attr_map = pd.read_csv(path.join(root_dir, "_data", "TEST_CALC", "input", "buildBldgFloodDepthTable6_prep_attr_map_INPUT_1.csv"))

    return prep_shp_path, pvals_csv_path, buildings_shp_path, results_shp_path, prep_attr_map

@pytest.fixture
def runMC_AALU_x4_output(get_test_data):
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    prep_df =  gpd.read_file(get_test_data[0], ignore_geometry=True)
    pval_df = gpd.read_file(get_test_data[1], ignore_geometry=True)
    prep_attr_map = get_test_data[4]

    bid_list = prep_df["BID"].to_list()

    bldg_ddf_lut_name = "Building_DDF_LUT_CPFRAworking.csv"
    inputs_obj = pfracoastal.Inputs(bddf_lut_path=path.join(path.abspath(path.dirname(path.dirname(__file__))),bldg_ddf_lut_name),
                                    use_outcsv=False, use_waves=True)
    out_df = pd.DataFrame()

    for bid in bid_list:
        temp_df = lib.runMC_AALU_x4(prep_df, pval_df, bid, inputs_obj, prep_attr_map)
        out_df = pd.concat([out_df, temp_df], ignore_index=True)

    return out_df

@pytest.fixture
def postprocessing_results(get_test_data, runMC_AALU_x4_output):
    # create a base to which to add run results AAL results
    bldg_df = gpd.read_file(get_test_data[2], ignore_geometry=True)
    runMC_AALU_x4_output.loc[:,"A"] = 1
    base_tab = pd.DataFrame(data={"BID":bldg_df.loc[:,"BID"], "ANLYS":[0 for i in range(bldg_df.shape[0])]})

    # join
	# field names hard-coded in runMC_AALU_x
    join_tab = base_tab.join(runMC_AALU_x4_output.set_index("BID"), on="BID", how="left").sort_values(by="ANLYS", axis=0)
    join_tab.loc[join_tab.query("A==1").index.to_list(), "ANLYS"] = 1
    join_tab.drop(columns=join_tab.columns.to_list()[-1], inplace=True)

    # replace NAs
    join_tab.iloc[join_tab["BAAL"].isna().to_list(), join_tab.columns.get_loc("BAAL")] = 0
    join_tab.iloc[join_tab["BAALmin"].isna().to_list(), join_tab.columns.get_loc("BAALmin")] = 0
    join_tab.iloc[join_tab["BAALmax"].isna().to_list(), join_tab.columns.get_loc("BAALmax")] = 0
    join_tab.iloc[join_tab["FLAG_DF16"].isna().to_list(), join_tab.columns.get_loc("FLAG_DF16")] = 0

    # add run results to results table
    results_df = bldg_df.join(join_tab.set_index("BID"), on="BID", how="left").sort_values(by="BID", axis=0)
    
    return results_df

def test_runMC_AALU_x4(get_test_data, postprocessing_results):
    comp_df = gpd.read_file(get_test_data[3], ignore_geometry=True)
    assert postprocessing_results.eq(comp_df).all().all()





