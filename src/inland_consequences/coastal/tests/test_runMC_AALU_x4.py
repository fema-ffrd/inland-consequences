from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd
import pandas as pd
import pytest

@pytest.fixture
def get_test_data():
    root_dir = path.abspath(path.dirname(__file__))
    test_dir = path.join(root_dir, "_data","TEST_CALC","output")

    prep_shp_path = path.join(test_dir, "Test1_PREP.shp")
    prep_df = gpd.read_file(prep_shp_path, ignore_geometry=True)

    pvals_csv_path = path.join(test_dir, "pvals.csv")
    pval_df = pd.read_csv(pvals_csv_path)

    buildings_shp_path = path.join(test_dir, "Test1_BUILDINGS.shp")
    buildings_df = gpd.read_file(buildings_shp_path, ignore_geometry=True)

    results_shp_path = path.join(test_dir, "Test1_RESULTS.shp")
    results_df = gpd.read_file(results_shp_path, ignore_geometry=True)

    return prep_df, pval_df, buildings_df, results_df

@pytest.fixture
def runMC_AALU_x4_output(get_test_data):
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    prep_df, pval_df = get_test_data[:2]
    bid_list = prep_df["BID"].to_list()

    inputs_obj = pfracoastal.PFRACoastal()
    out_df = pd.DataFrame()

    for bid in bid_list:
        temp_df = lib.runMC_AALU_x4(prep_df, pval_df, bid, inputs_obj)
        out_df = pd.concat([out_df, temp_df], ignore_index=True)

    return out_df

@pytest.fixture
def postprocessing_results(get_test_data, runMC_AALU_x4_output):
    # create a base to which to add run results AAL results
    bldg_df = get_test_data[2]
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
    comp_df = get_test_data[3]
    assert postprocessing_results.eq(comp_df).all().all()





