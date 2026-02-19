from inland_consequences.coastal import _pfracoastal_lib
import pandas as pd
import geopandas as gpd
import numpy as np
import pytest
from os import path

@pytest.fixture
def inputs():
    root_dir = path.abspath(path.dirname(__file__))
    test_dir = path.join(root_dir, "_data","TEST_CALC","output")
    csv_dir = path.join(test_dir, "TAB")

    pvals_csv_path = path.join(test_dir, 'pvals.csv')
    pvals_df = pd.read_csv(pvals_csv_path)

    bldg_shp_path = path.join(test_dir, "Test1_BUILDINGS.shp")
    bldg_df = gpd.read_file(bldg_shp_path, ignore_geometry=True)

    return pvals_df, csv_dir, bldg_df, test_dir

@pytest.fixture
def buildSampledLoss2_output(inputs):
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    pvals_df, csv_dir = inputs[:2]
    test_dir = inputs[3]
    bid_list = gpd.read_file(path.join(test_dir,"Test1_PREP.shp"), ignore_geometry=True)["BID"].to_list()
    out_df = pd.DataFrame()

    for bid in bid_list:
        cur_FBtab0_file_name = f"BID_{'0'*(6-len(str(bid)))}{bid}.csv"
        try:
            cur_FBtab0_df = pd.read_csv(path.join(csv_dir, cur_FBtab0_file_name))
        except:
            continue
        MCLossTab = lib.buildSampledLoss2(cur_FBtab0_df, pvals_df)
        
        in_bldg_flag = 0

        # get the flood table last entry
        cur_lastFBtab = cur_FBtab0_df.tail(1)
        if cur_FBtab0_df.notna().any().any() and pd.notna(cur_lastFBtab.loc[:,"PVAL"]).all():
            # check if sampled loss tab has frequencies lower than the last entry
		    #	if last entry is NA (normal) then nothing selected
            sel = MCLossTab.query(f"MC_prob < {cur_lastFBtab.loc[:,'PVAL']}").index.to_list()
            # if there is a selection, then replace all the affected sampled loss tab entries
		    #	with max losses
            if len(sel) > 0:
                in_bldg_flag = 1
                # Get the Max Damage set
                max_dams = cur_lastFBtab.loc[:,("Loss_Lw", "Loss_BE", "Loss_Up")]
                MCLossTab.iloc[sel, MCLossTab.columns.get_indexer(("Loss_Lw", "Loss_BE", "Loss_Up"))] = max_dams
        
        # if there are <2 loss values, then a curve cant be constructed. Loss = 0
        if MCLossTab.notna().query("MC_rp == True").shape[0] < 2:
            append_df = pd.DataFrame(data={"BID":bid, "BAAL":0, "BAALmin":0, "BAALmax":0, "FLAG_DF16":in_bldg_flag}, index=[0])
        else:
            append_df = pd.DataFrame(data={"BID":bid, 
                                           "BAAL":round(lib.Calc_Nrp_AnnLoss4(MCLossTab["MC_Be"], MCLossTab["MC_rp"]),0),
                                           "BAALmin":round(lib.Calc_Nrp_AnnLoss4(MCLossTab["MC_Lw"], MCLossTab["MC_rp"]),0),
                                           "BAALmax":round(lib.Calc_Nrp_AnnLoss4(MCLossTab["MC_Up"], MCLossTab["MC_rp"]),0), 
                                           "FLAG_DF16":in_bldg_flag
                                          },
                                     index=[0]
                                    )
        out_df = pd.concat((out_df, append_df), ignore_index=True)

    return out_df

@pytest.fixture
def postprocessing_results(inputs, buildSampledLoss2_output):
    # create a base to which to add run results AAL results
    buildSampledLoss2_output.loc[:,"A"] = 1
    base_tab = pd.DataFrame(data={"BID":inputs[2].loc[:,"BID"], "ANLYS":[0 for i in range(inputs[2].shape[0])]})

    # join
	# field names hard-coded in runMC_AALU_x
    join_tab = base_tab.join(buildSampledLoss2_output.set_index("BID"), on="BID", how="left").sort_values(by="ANLYS", axis=0)
    join_tab.loc[join_tab.query("A==1").index.to_list(), "ANLYS"] = 1
    join_tab.drop(columns=join_tab.columns.to_list()[-1], inplace=True)

    # replace NAs
    join_tab.iloc[join_tab["BAAL"].isna().to_list(), join_tab.columns.get_loc("BAAL")] = 0
    join_tab.iloc[join_tab["BAALmin"].isna().to_list(), join_tab.columns.get_loc("BAALmin")] = 0
    join_tab.iloc[join_tab["BAALmax"].isna().to_list(), join_tab.columns.get_loc("BAALmax")] = 0
    join_tab.iloc[join_tab["FLAG_DF16"].isna().to_list(), join_tab.columns.get_loc("FLAG_DF16")] = 0

    # add run results to results table
    results_df = inputs[2].join(join_tab.set_index("BID"), on="BID", how="left").sort_values(by="BID", axis=0)
    
    return results_df

def test_buildSampledLoss2(inputs, postprocessing_results):
    compare_df = gpd.read_file(path.join(inputs[3], "Test1_RESULTS.shp"), ignore_geometry=True)
    print(postprocessing_results.eq(compare_df))
    #postprocessing_results.to_csv('C:\\inland-consequences_costal_tool\\test_res3.csv')
    assert postprocessing_results.eq(compare_df).all().all()