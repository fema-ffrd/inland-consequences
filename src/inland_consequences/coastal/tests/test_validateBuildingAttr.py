from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
import pandas as pd
import geopandas as gpd
import os.path as pth

def test_validateBuildingAttr():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    test_inputs_obj = pfracoastal.Inputs()
    
    working_dir = pth.abspath(pth.dirname(__file__))

    in_shp = pth.join(working_dir, r"_data/TEST_CALC/input/Calc_bldg_sample.shp")
    test_intab = gpd.read_file(in_shp, ignore_geometry=True)
    
    correct_output_shp = pth.join(working_dir, r"_data/TEST_CALC/output/Test1_BUILDINGS.shp")
    correct_output_tab = gpd.read_file(correct_output_shp, ignore_geometry=True)

    # set unique BIDs
    test_intab["BID"] = list(range(1,test_intab.shape[0]+1))

    # sort the columns to be in the same order they appear in the 'IN' column of bldg_attr_map
    test_intab = test_intab.loc[:,test_inputs_obj.bldg_attr_map["IN"].to_list()]

    # rename columns
    name_dict = {in_name:out_name for in_name,out_name in list(zip(test_inputs_obj.bldg_attr_map["IN"].to_list(), test_inputs_obj.bldg_attr_map["OUT"].to_list()))}
    test_intab.rename(columns=name_dict, inplace=True)

    ret = lib.validateBuildingAttr(test_inputs_obj, test_intab)
    print(ret.eq(correct_output_tab).all())
    #print(ret.loc[:,["STORY","FOUND","BASEFIN"]])
    #print(correct_output_tab.loc[:,["STORY","FOUND","BASEFIN"]])
    assert ret.eq(correct_output_tab).all().all() == True