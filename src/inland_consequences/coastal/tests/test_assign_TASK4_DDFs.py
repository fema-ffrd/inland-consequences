from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd
import pandas as pd

def test_assign_TASK4_DDFs():
    working_dir = path.abspath(path.dirname(__file__))

    in_bldg_shp_path = path.join(working_dir, "_data/TEST_CALC/input/Calc_bldg_sample.shp")
    in_wav_shp_path = path.join(working_dir, "_data/TEST_CALC/output/Test1_WAV.shp")
    in_wse_shp_path = path.join(working_dir, "_data/TEST_CALC/output/Test1_WSE.shp")

    lib = _pfracoastal_lib._PFRACoastal_Lib()
    # these properties are not what they would normally be set to if running main
    inputs_obj = pfracoastal.Inputs(
        bldg_path=in_bldg_shp_path, 
        swelA_path=in_wse_shp_path,
        use_waves=True,
        waveA_path=in_wav_shp_path
    )
    
    bldg_gdf = lib.formatBuildings(inputs_obj)
    bldg_geom = bldg_gdf[bldg_gdf.active_geometry_name]
    bldg_gdf_crs = bldg_gdf.crs
    
    #bldg_tab = bldg_gdf.to_wkb().drop(columns=bldg_gdf.active_geometry_name)
    wav_tab = gpd.read_file(inputs_obj.waveA_path, ignore_geometry=True)
    wse_tab = gpd.read_file(inputs_obj.swelA_path, ignore_geometry=True)

    # create extensible swel attribute map
    temp_tab = gpd.read_file(path.join(working_dir,"_data/TEST_CALC/input/Calc_SWL_BE_sample.shp"), ignore_geometry=True)

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
    wv_attr_map = swel_attr_map
    sel = wv_attr_map.query("CHECK == 1").loc[:,"OUT"].index.to_list()
    wv_attr_map.iloc[sel, wv_attr_map.columns.get_loc("OUT")] = wv_attr_map.iloc[sel, wv_attr_map.columns.to_list().index("OUT")].apply(lambda x: x.replace('s','w'))
    wv_attr_map["DESC"] = wv_attr_map["DESC"].apply(lambda x: x.replace('surge','wave'))
    wv_attr_map["DESC"] = wv_attr_map["DESC"].apply(lambda x: x.replace('elevation','height'))

    # create wverr attribute map
    wverr_attr_map = wv_attr_map
    sel = wverr_attr_map.query("DESC == 'wave height'").index.to_list()
    wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("OUT")] = wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("OUT")].apply(lambda x: x.replace('surge','wave'))
    wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("DESC")] = wverr_attr_map.iloc[sel,wverr_attr_map.columns.get_loc("DESC")].apply(lambda x: x.replace('elevation','height'))

    # BUILD the WSE Attribute map for tracking field names
    wse_attr_dict = {
        "OUT": inputs_obj.bldg_attr_map.query("(DESC == 'new building id') or (DESC == 'ground elevation')").loc[:,"OUT"].to_list()+["VALID","spt1","spt2","spt3"]+swel_attr_map.query("DDC == 1").loc[:,"OUT"].to_list()+swerr_attr_map.query("DDC == 1").loc[:,"OUT"].to_list()+wv_attr_map.query("DDC == 1").loc[:,"OUT"].to_list()+wverr_attr_map.query("DDC == 1").loc[:,"OUT"].to_list(),
        "DESC": ["new building id","ground elevation","valid for analysis","NNsurgeID","NNsurgeID","NNsurgeID"]+['surge elevation' for i in range(swel_attr_map.query("DDC == 1").shape[0])]+['surge error' for i in range(swerr_attr_map.query("DDC == 1").shape[0])]+['wave height' for i in range(wv_attr_map.query("DDC == 1").shape[0])]+['wave error' for i in range(wverr_attr_map.query("DDC == 1").shape[0])],
        "PREP":[1,0,0,0,0,0]+[1 for i in range(swel_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(swerr_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(wv_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(wverr_attr_map.query("DDC == 1").shape[0])],
        "JOIN":[1,0,0,0,0,0]+[1 for i in range(swel_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(swerr_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(wv_attr_map.query("DDC == 1").shape[0])]+[1 for i in range(wverr_attr_map.query("DDC == 1").shape[0])]
    }
    wse_attr_map = pd.DataFrame(wse_attr_dict)
    del wse_attr_dict

    # append wave data to swel data
    wv_fields = wv_attr_map.query("DESC == 'wave height'").loc[:,'OUT'].to_list()
    wverr_fields = wverr_attr_map.query("DESC == 'wave error'").loc[:,'OUT'].to_list()

    full_tab = wse_tab.join(wav_tab.loc[:, ["BID"]+wv_fields+wverr_fields], on="BID", how="left", lsuffix="_wse", rsuffix='_wav')
    full_tab = full_tab.drop(columns=['BID_wse', 'BID_wav']).sort_values("BID")

    full_gdf = gpd.GeoDataFrame(data=full_tab, geometry=bldg_geom, crs=bldg_gdf_crs)

    # select previously identified valid points
    sel = full_gdf.query("VALID == 1", inplace=False).index.to_list()
    full_geom = full_gdf.iloc[sel, full_gdf.columns.get_loc(full_gdf.active_geometry_name)]
    full_gdf_crs = full_gdf.crs
    val_gdf = gpd.GeoDataFrame(data=full_tab.iloc[sel], geometry=full_geom, crs=full_gdf_crs)
    del full_geom, full_gdf_crs

    # because VAL.SPDF is filtered, need to similarly filter the building file
    # get the IDs of the valid buildings
    sel = bldg_gdf.loc[:,"BID"].isin(val_gdf.loc[:,"BID"]).to_list()

    # grab the building attribute table and keep only the records corresponding to valid buildings
    test_bldgred_tab = bldg_gdf.to_wkb().drop(columns=bldg_gdf.active_geometry_name).loc[sel,inputs_obj.bldg_attr_map.query("ANLYS == 1").loc[:,"OUT"].to_list()]
    
    # add sort field because bldg.tab and bldg.coords are 1:1 and .tab might get jumbled in future merges or joins
    test_bldgred_tab["sort"] = [i for i in range(1, test_bldgred_tab.shape[0]+1)]

    # DDFS
	# Assign DDFs to buildings
    # Select Four TASK4 DDFs, 1 for freshwater intrusion, 1 each for low-wave, med-wave, and 
	# high-wave conditions
    ret = lib.assign_TASK4_DDFs(inputs_obj, test_bldgred_tab)

    # add DDF IDs as attributes to bldgred.tab
    test_bldgred_tab["DDF1"] = ret.loc[:,"DDF1"]
    test_bldgred_tab["DDF2"] = ret.loc[:,"DDF2"]
    test_bldgred_tab["DDF3"] = ret.loc[:,"DDF3"]
    test_bldgred_tab["DDF4"] = ret.loc[:,"DDF4"]

    # placeholder for future Erosion DDFs
    test_bldgred_tab["DDFE"] = list(range(test_bldgred_tab.shape[0]))

    # merge wsels to bldg attributes and format
    sel = wse_attr_map.query("PREP == 1").loc[:,"OUT"].to_list()
    prep_tab = test_bldgred_tab.join(val_gdf.to_wkb().drop(columns=val_gdf.active_geometry_name).loc[:,sel], on="BID", lsuffix="_prep", rsuffix='_val')
    
    # sort to ensure proper order with VAL.SPDF@coords, then remove any extra field
    prep_tab = prep_tab.sort_values("sort")
    prep_tab.index = list(range(prep_tab.shape[0]))
    prep_tab = prep_tab.drop(columns=["sort", "BID_prep", "BID_val"])

    # build output SPDF
    test_prep_gdf = gpd.GeoDataFrame(data=prep_tab, geometry=val_gdf[val_gdf.active_geometry_name], crs=val_gdf.crs)

    # create a copy of PREP for writing output that converts NA to -99999 so ESRI SHP doesnt 
	# auto-convert NA to 0.
    test_prep_df = test_prep_gdf.to_wkb().drop(columns=test_prep_gdf.active_geometry_name)
    test_prep_df = test_prep_df.mask(test_prep_df.isna(), pd.to_numeric(swel_attr_map.iat[1,swel_attr_map.columns.get_loc("DEF")]))

    # check results
    comp_prep_shp_path = path.join(working_dir, "_data/TEST_CALC/output/Test1_PREP.shp")
    comp_prep_df = gpd.read_file(comp_prep_shp_path, ignore_geometry=True)

    assert test_prep_df.loc[:,["DDF1","DDF2","DDF3","DDF4"]].eq(comp_prep_df.loc[:,["DDF1","DDF2","DDF3","DDF4"]]).all().all()