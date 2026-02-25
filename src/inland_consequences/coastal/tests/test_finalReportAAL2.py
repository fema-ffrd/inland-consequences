from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
from os import path, remove
import geopandas as gpd
import pytest
import logging

logger = logging.getLogger("pfraCoastal")

@pytest.fixture
def test_inputs():
    root_dir = path.abspath(path.dirname(__file__))
    out_data_dir = path.join(root_dir, "_data", "TEST_CALC", "output")

    results_shp = path.join(out_data_dir, "TEST1_RESULTS.shp")
    out_log = path.join(out_data_dir, "finalReportAAL2_OUTPUT.log")

    return results_shp, out_log

def test_finalReportAAL2(test_inputs):
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    if path.exists(test_inputs[1]):
        remove(test_inputs[1])

    fh = logging.FileHandler(test_inputs[1])
    fh.setLevel("INFO")
    ch = logging.StreamHandler()
    ch.setLevel("INFO")
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)

    results_df = gpd.read_file(test_inputs[0])
    attr_map = pfracoastal.Inputs().bldg_attr_map

    lib.finalReportAAL2(results_tab=results_df, prep_attr_map=attr_map)
    logging.shutdown()

    assert path.exists(test_inputs[1]) and path.getsize(test_inputs[1]) > 0