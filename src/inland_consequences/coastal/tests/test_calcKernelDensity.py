from inland_consequences.coastal import _pfracoastal_lib
import pandas as pd
from os import path, mkdir, remove
import geopandas as gpd
import pytest
import scipy
import rasterio
import numpy as np

@pytest.fixture
def make_test_heatmap():
    lib = _pfracoastal_lib._PFRACoastal_Lib()

    root_dir = path.abspath(path.dirname(__file__))
    test_data_dir = path.join(root_dir, "_data/TEST_CALC/output")
    tmp_dir = path.join(root_dir, "_data/TEST_CALC/tmp")

    results_shp = path.join(test_data_dir, "Test1_RESULTS.shp")
    test_heatmap_tif = path.join(test_data_dir, "Test1_heatmap.tif")

    results_gdf = gpd.read_file(results_shp)
    results_geometry = results_gdf.geometry
    results_coords_array = results_geometry.get_coordinates().to_numpy()

    # conversion for sq ft to acres
    sqft2acres = 43560
    hm_bandwidth = 1100
    hm_resolution = 500
    aal_tab = results_gdf.drop(columns=results_gdf.geometry.name)
    aal_field = "BAAL"

    # create starting grid with value 0
    with rasterio.open(test_heatmap_tif, 'r', driver="GTiff") as test_hm:
        out_width = test_hm.width
        out_height = test_hm.height
        out_crs = test_hm.crs
        out_transform = test_hm.transform
        out_dtype = test_hm.dtypes[0]
        out_nodata = test_hm.nodata
    
    # set up tmp dir and paths
    if not path.exists(tmp_dir):
        mkdir(tmp_dir)

    temp_raster_file = path.join(tmp_dir, "tmpTestHm.tif")
    if path.exists(temp_raster_file):
        remove(temp_raster_file)

    # cycle through each cell and calculate KDE
    kde_mat = np.zeros(shape=(out_height, out_width))
    
    with rasterio.open(temp_raster_file, 'w+', "GTiff", out_width, out_height, count=1, dtype=out_dtype, crs=out_crs, transform=out_transform, nodata=out_nodata) as out_hm:
        out_hm.write(kde_mat,1)
        for row in range(out_height):
            for col in range(out_width):
                # get xcoord and ycoord of cell
                cur_cell_centroid = np.array(out_hm.xy(row,col)).reshape(1,2)
                #calc NN
                bpt_dist = scipy.spatial.distance.cdist(results_coords_array, cur_cell_centroid, metric='euclidean')
                # filter for points that are inside the search radius
                bpt_df = pd.DataFrame().from_dict({
                    "BID":aal_tab["BID"].to_list(),
                    "AAL": aal_tab[f"{aal_field}"].to_list(),
                    "Dist":bpt_dist.flatten().tolist()
                })
                bpt_sel = bpt_df.query(f"Dist <= {hm_bandwidth}")
                
                if bpt_sel.shape[0] > 0:
                    kde_mat[row,col] = lib.calcKernelDensity(bpt_sel, hm_bandwidth)*sqft2acres

        out_hm.write(kde_mat,1)
    return temp_raster_file

def test_calcKernelDensity(make_test_heatmap):
    root_dir = path.abspath(path.dirname(__file__))
    test_data_dir = "_data/TEST_CALC/output"
    correct_heatmap_tif = path.join(root_dir, test_data_dir, "Test1_heatmap.tif")

    with rasterio.open(correct_heatmap_tif, 'r', driver="GTiff") as correct_hm:
        correct_hm_ul_xy = correct_hm.transform * (0,0)
        correct_hm_vals = correct_hm.read(1)

    with rasterio.open(make_test_heatmap, 'r', driver="GTiff") as test_hm:
        test_hm_ul_xy = test_hm.transform * (0,0)
        test_hm_vals = test_hm.read(1)

    ul_check = correct_hm_ul_xy == test_hm_ul_xy
    val_check = np.equal(correct_hm_vals,test_hm_vals).all()

    assert ul_check and val_check