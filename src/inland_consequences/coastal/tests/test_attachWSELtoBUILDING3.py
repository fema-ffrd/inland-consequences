from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd
import pandas as pd
from scipy.stats import norm
import numpy as np
import pytest

@pytest.fixture
def in_out_dir():
    root_dir = path.abspath(path.dirname(__file__))
    input_dir = path.join(root_dir, "_data/TEST_CALC/input")
    output_dir = path.join(root_dir, "_data/TEST_CALC/output")
    return input_dir, output_dir

@pytest.fixture
def bldg_surge_data(in_out_dir):
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    in_dir,out_dir = in_out_dir

    #get building shapefile and gdf
    bldg_shp = path.join(out_dir, "Test1_BUILDINGS.shp")
    bldg_gdf = gpd.read_file(bldg_shp)

    #build swel & swerr attr maps
    temp_tab = gpd.read_file(path.join(in_dir, "Calc_SWL_BE_sample.shp"), ignore_geometry=True)
    temp_cols = [col for col in temp_tab.columns.to_list() if col[0]=='e']
    rp_avail = [lib.removeNonNumeric(col) for col in temp_cols]

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
    
    swerr_attr_map = swel_attr_map.copy()
    swerr_attr_map["OUT"] = swerr_attr_map["OUT"].apply(lambda x: x.replace("s", "sx") if x!="SID" else x)
    swerr_attr_map['DESC'] = swerr_attr_map['DESC'].apply(lambda x: 'surge error' if x!="node id" else x)
    
    # load swel A and swel B
    swel_a = path.join(in_dir,"Calc_SWL_BE_sample.shp")
    swel_b = path.join(in_dir, "Calc_SWL_84_sample.shp")

    psurge_gdf = lib.formatSurge(swel_a, swel_attr_map)
    psurge84_gdf = lib.formatSurge(swel_b, swel_attr_map)
    psurgerr_gdf = psurge84_gdf.copy()

    psurge_df = psurge_gdf.to_wkb().drop(columns=psurge_gdf.geometry.name)
    psurge84_df = psurge84_gdf.to_wkb().drop(columns=psurge84_gdf.geometry.name)
    psurgerr_df = psurge84_df.copy()
    

    rename_map = {psurgerr_df.columns.to_list()[i]:swerr_attr_map.iat[i,1] for i in range(psurgerr_df.columns.size)}
    psurgerr_df = psurgerr_df.rename(columns=rename_map)

    minus_tab = psurgerr_df

    # create a copy of PSURGE and PSURGE84 that converts -99999 to NA for calculating differences
    psurge_df_copy = psurge_df.copy() 
    psurge84_df_copy = psurge84_df.copy()
    psurge_df_copy.mask(psurge_df_copy < -999, pd.NA, inplace=True)
    psurge84_df_copy.mask(psurge84_df_copy < -999, pd.NA, inplace=True)

    minus_tab.iloc[:,1:] = psurge84_df_copy.iloc[:,1:].sub(psurge_df_copy.iloc[:,1:])
    minus_tab.mask(minus_tab.lt(0), 0, inplace=True)
    psurgerr_df = minus_tab
    psurgerr_df.mask(psurgerr_df.isna(), pd.to_numeric(swerr_attr_map.iat[swerr_attr_map.shape[0]-1,4]), inplace=True)

    # Find the fully NULL nodes in PSURGE .
	# remove those features from each feature class
    good_rows = psurge_df.iloc[:,swel_attr_map.shape[0]-1].ne(swel_attr_map["DEF"].iat[-1]).to_list()
    psurge_data = psurge_df.iloc[good_rows,:]
    psurge_geom = psurge_gdf.geometry.iloc[good_rows]

    psurgerr_data = psurgerr_df.iloc[good_rows,:]
    psurgerr_geom = psurgerr_gdf.geometry.iloc[good_rows]
    
    psurge_crs = psurge_gdf.crs
    psurgerr_crs = psurgerr_gdf.crs
    
    out_psurge_gdf = gpd.GeoDataFrame(data=psurge_data, geometry=psurge_geom, crs=psurge_crs)
    out_psurgerr_gdf = gpd.GeoDataFrame(data=psurgerr_data, geometry=psurgerr_geom, crs=psurgerr_crs)

    return bldg_gdf, swel_attr_map, swerr_attr_map, out_psurge_gdf, out_psurgerr_gdf

@pytest.fixture
def attachWSELtoBUILDING3_output(bldg_surge_data):
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    bldg_gdf = bldg_surge_data[0]
    bldg_df = bldg_gdf.to_wkb().drop(columns=bldg_gdf.geometry.name)

    swel_attr_map, swerr_attr_map = bldg_surge_data[1:3]
    psurge_gdf, psurgerr_gdf = bldg_surge_data[3:5]

    bldg_coords_array = bldg_gdf.geometry.get_coordinates().to_numpy()

    psurge_output = pd.DataFrame()
    psurgerr_output = pd.DataFrame()
    for i in range(bldg_df.shape[0]):
        temp_output1 = lib.attachWSELtoBUILDING3(bldg_df.iloc[i,:], bldg_coords_array[i], psurge_gdf, swel_attr_map)
        psurge_output = pd.concat([psurge_output, temp_output1], ignore_index=True)

        # only if use uncertainty is true when in main()
        temp_output2 = lib.attachWSELtoBUILDING3(bldg_df.iloc[i,:], bldg_coords_array[i], psurgerr_gdf, swerr_attr_map)
        psurgerr_output = pd.concat([psurgerr_output, temp_output2], ignore_index=True)

    return psurge_output, psurgerr_output

@pytest.fixture
def postprocessing_output(bldg_surge_data, attachWSELtoBUILDING3_output):
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    bldg_gdf = bldg_surge_data[0]
    swel_attr_map, swerr_attr_map = bldg_surge_data[1:3]
    psurge_output, psurgerr_output = attachWSELtoBUILDING3_output[:2]

    out_tab = psurge_output.apply(pd.to_numeric, axis='index')
    out_tab_2 = psurgerr_output.apply(pd.to_numeric, axis='index')

    out_tab_3 = out_tab_2.loc[:,["BID"]+swerr_attr_map.query("DESC == 'surge error'")["OUT"].to_list()]
    out_tab_1 = out_tab.join(out_tab_3.set_index("BID"), on="BID", how="left").sort_values(by=["BID"])

    tabWet = out_tab_1.loc[:,["DEMFT", "s10000", "sx10000"]].apply(lambda x: 1-norm.cdf(lib.getZscore(x.iat[0], x.iat[1], x.iat[2])), axis=1, result_type="reduce")

    sel = tabWet.ge(0.05).to_list()
    out_tab_1.loc[sel,"VALID"] = 1

    sel = out_tab_1["DEMFT"].le(-999).to_list()
    out_tab_1.loc[sel,"VALID"] = 0
    out_tab_1.mask(out_tab_1.isna(), pd.to_numeric(swel_attr_map["DEF"].iat[2]), inplace=True)
    out_wse_gdf = gpd.GeoDataFrame(data=out_tab_1, geometry=bldg_gdf.geometry, crs=bldg_gdf.geometry.crs)
    
    return out_wse_gdf

def test_attachWSELtoBUILDING3(in_out_dir, postprocessing_output):
    out_dir = in_out_dir[1]
    test_wse_gdf = postprocessing_output
    correct_wse_gdf = gpd.read_file(path.join(out_dir, "Test1_WSE.shp"))
    #print(test_wse_gdf.loc[:,['spt1','spt2','spt3']])
    #print(correct_wse_gdf.loc[:,['spt1','spt2','spt3']])
    print(correct_wse_gdf.eq(test_wse_gdf).any())
    assert test_wse_gdf.eq(correct_wse_gdf).all().all()
