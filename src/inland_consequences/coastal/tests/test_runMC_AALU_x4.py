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
    
    temp_tab = gpd.read_file(path.join(root_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.shp"), ignore_geometry=True)

    #get all names that begin with 'e'
    temp_cols = [col for col in temp_tab.columns.to_list() if col[0]=='e']

    #get the numeric portion of those columns
    rp_avail = [lib.removeNonNumeric(col) for col in temp_cols]

    # add these to the attribute map
    swel_attr_dict = {
        "IN":["SID"]+temp_cols,
        "OUT":["SID"]+['s'+col for col in rp_avail],
        "DESC":["node id"]+["surge elevation" for i in range(len(temp_cols))],
        "TYPE":['int32' for i in range(len(["SID"]+temp_cols))],
        "DEF":[-99999 for i in range(len(["SID"] + temp_cols))],
        "CHECK":[0]+[1 for i in range(len(temp_cols))],
        "DDC":[0]+[1 for i in range(len(temp_cols))]
    }
    swel_attr_map = pd.DataFrame(swel_attr_dict)

    # creat swerr attribute map
    swerr_attr_map = swel_attr_map
    sel = swerr_attr_map.query("DESC == 'surge_elevation'").index.to_list()
    swerr_attr_map.iloc[sel, swerr_attr_map.columns.get_loc("OUT")] = swerr_attr_map.iloc[sel, swerr_attr_map.columns.get_loc("OUT")].apply(lambda x: x.replace("s","sx"))
    swerr_attr_map.iloc[sel, swerr_attr_map.columns.get_loc("OUT")] = swerr_attr_map.iloc[sel, swerr_attr_map.columns.get_loc("DESC")].apply(lambda x: 'surge error' if x!='node id' else x)
    
    # create extensible wave attribute map
    wv_attr_map = swel_attr_map.copy()
    sel = wv_attr_map.query("CHECK == 1").loc[:,"OUT"].index.to_list()
    wv_attr_map.iloc[sel, wv_attr_map.columns.get_loc("OUT")] = wv_attr_map.iloc[sel, wv_attr_map.columns.to_list().index("OUT")].apply(lambda x: x.replace('s','w'))
    wv_attr_map["DESC"] = wv_attr_map["DESC"].apply(lambda x: x.replace('surge','wave'))
    wv_attr_map["DESC"] = wv_attr_map["DESC"].apply(lambda x: x.replace('elevation','height'))

    # create wverr attribute map
    wverr_attr_map = wv_attr_map.copy()
    sel = wverr_attr_map.query("DESC == 'wave height'").index.to_list()
    #wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("OUT")] = wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("OUT")].apply(lambda x: x.replace('surge','wave'))
    #wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("DESC")] = wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("DESC")].apply(lambda x: x.replace('elevation','height'))
    wverr_attr_map.iloc[sel, wverr_attr_map.columns.get_loc("DESC")] = 'wave error'
    wverr_attr_map.iloc[sel, wverr_attr_map.columns.get_loc("OUT")] = wverr_attr_map.iloc[sel, wverr_attr_map.columns.get_loc("OUT")].apply(lambda x: x.replace("w","wx"))

    # create prep_attr_map
    prep_attr_dict = {
        "OUT":inputs_obj.bldg_attr_map.query('ANLYS == 1')["OUT"].to_list()+["DDF1","DDF2","DDF3","DDF4","DDFE"]+swel_attr_map.query('DDC == 1')["OUT"].to_list()+swerr_attr_map.query('DDC == 1')["OUT"].to_list()+wv_attr_map.query('DDC == 1')["OUT"].to_list()+wverr_attr_map.query('DDC == 1')["OUT"].to_list(),
        "DESC":inputs_obj.bldg_attr_map.query('ANLYS == 1')["DESC"].to_list()+["DDF ID" for i in range(4)]+["DDF Erosion"]+["surge elevation" for i in range(swel_attr_map.query('DDC == 1').shape[0])]+["surge error" for i in range(swerr_attr_map.query('DDC == 1').shape[0])]+["wave height" for i in range(wv_attr_map.query('DDC == 1').shape[0])]+["wave error" for i in range(wverr_attr_map.query('DDC == 1').shape[0])]
    }
    prep_attr_map = pd.DataFrame(prep_attr_dict)

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
                                    use_outcsv=False)
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





