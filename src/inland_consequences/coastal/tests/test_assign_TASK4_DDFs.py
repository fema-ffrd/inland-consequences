from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd
import pandas as pd

def test_assign_TASK4_DDFs():
    working_dir = path.abspath(path.dirname(__file__))

    in_bldg_shp_path = path.join(working_dir, "_data/TEST_CALC/input/Calc_bldg_sample.shp")
    in_wav_shp_path = path.join(working_dir, "_data/TEST_CALC/output/Test1_WAV.shp")
    in_swel_shp_path = path.join(working_dir, "_data/TEST_CALC/output/Test1_WSE.shp")

    lib = _pfracoastal_lib._PFRACoastal_Lib()
    inputs_obj = pfracoastal.Inputs(
        bldg_path=in_bldg_shp_path, 
        swelA_path=in_swel_shp_path,
        use_waves=True,
        waveA_path=in_wav_shp_path
    )

    bldg_gdf = lib.formatBuildings(inputs_obj)
    wav_tab = gpd.read_file(inputs_obj.waveA_path, ignore_geometry=True)
    wse_tab = gpd.read_file(inputs_obj.swelA_path, ignore_geometry=True)

    # create extensible swel attribute map
    temp_tab = gpd.read_file(inputs_obj.swelA_path, ignore_geometry=True)

    #get all names that begin with 'e'
    temp_cols = [col for col in temp_tab.columns.to_list() if col[0]=='e']

    #get the numeric portion of those columns
    rp_avail = [lib.removeNonNumeric(col) for col in temp_cols]

    # add these to the attribute map
    swel_attr_dict = {
        "IN":["SID"].extend(temp_cols),
        "OUT":["SID"].extend(['s'+col for col in rp_avail]),
        "DESC":["node id"].extend(["surge elevation" for i in range(len(temp_cols))]),
        "TYPE":['int32' for i in range(len(["SID"].extend(temp_cols)))],
        "DEF":[-99999 for i in range(len(["SID"].extend(temp_cols)))],
        "CHECK":[0].extend([1 for i in range(len(temp_cols))]),
        "DDC":[0].extend([1 for i in range(len(temp_cols))])
    }
    swel_attr_map = pd.DataFrame(swel_attr_dict)

    # create extensible wave attribute map
    wv_attr_map = swel_attr_map
    sel = wv_attr_map.query("CHECK == 1").index.to_list()
    wv_attr_map = wv_attr_map.rename(columns={name:name.replace('s','w') for name in wv_attr_map.loc[:,"OUT"].iloc(sel).to_list()})
    wv_attr_map.loc[:,"DESC"] = [desc.replace('surge', 'wave') for desc in wv_attr_map.loc[:,"DESC"].to_list()]
    wv_attr_map.loc[:,"DESC"] = [desc.replace('elevation', 'height') for desc in wv_attr_map.loc[:,"DESC"].to_list()]

    # create wverr attr map
    wverr_attr_map = wv_attr_map
    sel = wverr_attr_map.query("DESC == 'wave height'")
    wverr_attr_map.loc[:,"OUT"].iloc[sel] = [name.replace('w','wx') for name in wverr_attr_map.loc[:,"OUT"].iloc[sel].to_list()]
    wverr_attr_map.loc[:,"DESC"].iloc[sel] = [name.replace('height', 'error') for name in wverr_attr_map.loc[:,"DESC"].iloc[sel].to_list()]

    # append wave data to swel data
    wv_fields = wv_attr_map.query("DESC == 'wave height'").loc[:,'OUT'].to_list()
    wverr_fields = wverr_attr_map.query("DESC == 'wave error'").loc[:,'OUT'].to_list()
    full_tab = wse_tab.join(wav_tab[:, ["BID"].extend(wv_fields + wverr_fields)], on="BID", how="left")
    full_tab = full_tab.sort_values("BID")

    # select previously identified valid points
    val_tab = full_tab.query("VALID == 1")

    # because VAL.SPDF is filtered, need to similarly filter the building file
    # get the IDs of the valid buildings
    bldg_tab = bldg_gdf.to_wkb().drop(columns=bldg_gdf.active_geometry_name)
    sel = bldg_tab.loc[:,"BID"].isin(val_tab.loc[:,"BID"]).to_list()

    # grab the building attribute table and keep only the records corresponding to valid buildings
    test_bldgred_tab = bldg_tab.loc[:,inputs_obj.bldg_attr_map.query("ANLYS == 1").loc[:,"OUT"].to_list()].iloc[sel]
    
    # add sort field because bldg.tab and bldg.coords are 1:1 and .tab might get jumbled in future merges or joins
    test_bldgred_tab["sort"] = [i for i in range(1, test_bldgred_tab.shape[0]+1)]

    # DDFS
	# Assign DDFs to buildings
    # Select Four TASK4 DDFs, 1 for freshwater intrusion, 1 each for low-wave, med-wave, and 
	# high-wave conditions
    ret = lib.assign_TASK4_DDFs(inputs_obj, test_bldgred_tab)

    # get output prep data, subset it down, then check ret against it
    prep_shp_path = path.join(working_dir,"_data/TEST_CALC/output/Test1_PREP.shp")
    prep_tab = gpd.read_file(prep_shp_path, ignore_geometry=True)
    prep_ddf_tab = prep_tab.loc[:,["BID", "DDF1", "DDF2", "DDF3", "DDF4"]].sort_values("BID").drop(columns="BID")
    assert ret.eq(prep_ddf_tab).all().all()