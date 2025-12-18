from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path
import geopandas as gpd

def test_formatBuildings():
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    root_dir = path.abspath(path.dirname(__file__))

    test_bldg_path = path.join(root_dir, r"_data/TEST_CALC/input/Calc_bldg_sample.shp")
    test_inputs = pfracoastal.Inputs(bldg_path=test_bldg_path)

    correct_output_shp_path = path.join(root_dir, r"_data/TEST_CALC/output/Test1_BUILDINGS.shp")
    correct_out_gdf = gpd.read_file(correct_output_shp_path)

    ret = lib.formatBuildings(test_inputs)
    assert ret.eq(correct_out_gdf).all().all()