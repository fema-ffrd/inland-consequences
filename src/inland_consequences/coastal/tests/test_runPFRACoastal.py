from inland_consequences.coastal import _pfracoastal_lib, pfracoastal
import pytest
from os import path, listdir, mkdir
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio

@pytest.fixture
def inputs_obj():
    test_use_out_csv = True
    test_use_heatmap = True
    test_proj_prefix = 'TEST'
    output_dir = path.join(path.abspath(path.dirname(__file__)), "_data", "run_PFRACoastal_output")

    if not path.exists(output_dir):
        mkdir(output_dir)

    test_data_dir = path.join(path.abspath(path.dirname(__file__)), "_data", "TEST_CALC", "input")
    in_bldgs = path.join(test_data_dir, "Calc_bldg_sample.shp")
    in_swelA = path.join(test_data_dir, "Calc_SWL_BE_sample.shp")
    in_swelB = path.join(test_data_dir, "Calc_SWL_84_sample.shp")
    in_waveA = path.join(test_data_dir, "Calc_Hc_BE_sample.shp")
    in_waveB = path.join(test_data_dir, "Calc_Hc_84_sample.shp")
    in_bldg_ddf_lut = path.join(path.abspath(path.dirname(path.dirname(__file__))), 'Building_DDF_LUT_CPFRAworking.csv')
    in_storm_csv = ''
    
    ret = pfracoastal.Inputs(use_outcsv=test_use_out_csv,
                             use_heatmap=test_use_heatmap,
                             bldg_path=in_bldgs,
                             swelA_path=in_swelA,
                             swelB_path=in_swelB,
                             waveA_path=in_waveA,
                             waveB_path=in_waveB,
                             bddf_lut_path=in_bldg_ddf_lut,
                             storm_csv=in_storm_csv,
                             proj_prefix=test_proj_prefix,
                             out_shp_path=output_dir,
                             blabber=False
                             )
    
    return ret


@pytest.fixture
def test_datasets():
    test_data_dir = path.join(path.abspath(path.dirname(__file__)), "_data", "TEST_CALC", "output")
    test_proj_prefix = 'Test1'
    test_hm_name = 'heatmap'

    path_dict = {
        'BUILDINGS.shp':path.join(test_data_dir, f'{test_proj_prefix}_BUILDINGS.shp'),
        'WSE.shp':path.join(test_data_dir, f'{test_proj_prefix}_WSE.shp'),
        'WAV.shp':path.join(test_data_dir, f'{test_proj_prefix}_WAV.shp'),
        'PREP.shp':path.join(test_data_dir, f'{test_proj_prefix}_PREP.shp'),
        'RESULTS.shp':path.join(test_data_dir, f'{test_proj_prefix}_RESULTS.shp'),
        'TAB':path.join(test_data_dir, 'TAB'),
        'pvals.csv':path.join(test_data_dir, 'pvals.csv'),
        'heatmap.tif':path.join(test_data_dir, f'{test_proj_prefix}_{test_hm_name}.tif')
    }

    return path_dict


def test_runPFRACoastal(inputs_obj):
    pfra = pfracoastal.PFRACoastal()
    ret = pfra.runPFRACoastal(inputs_obj)
    assert ret is None


def test_verify_buildings_shp(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_BUILDINGS.shp")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_gdf = gpd.read_file(output_data_path)
    test_gdf = gpd.read_file(test_data_path)

    chk = output_gdf.eq(test_gdf).all().all()
    assert chk


def test_verify_wse_shp(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_WSE.shp")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_gdf = gpd.read_file(output_data_path)
    test_gdf = gpd.read_file(test_data_path)

    chk = output_gdf.eq(test_gdf).all().all()
    assert chk


def test_verify_wav_shp(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_WAV.shp")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_gdf = gpd.read_file(output_data_path)
    test_gdf = gpd.read_file(test_data_path)

    chk = output_gdf.eq(test_gdf).all().all()
    assert chk


def test_verify_prep_shp(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_PREP.shp")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_gdf = gpd.read_file(output_data_path)
    test_gdf = gpd.read_file(test_data_path)

    chk = output_gdf.eq(test_gdf).all().all()
    assert chk


def test_verify_results_shp(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_RESULTS.shp")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_gdf = gpd.read_file(output_data_path)
    test_gdf = gpd.read_file(test_data_path)

    chk = output_gdf.eq(test_gdf).all().all()
    assert chk


def test_verify_loss_tab_folder(inputs_obj, test_datasets):
    output_tab_folder = path.join(inputs_obj.out_shp_path, "TAB")
    test_tab_folder = test_datasets[path.basename(output_tab_folder).split('_')[-1]]

    if inputs_obj.use_outcsv:
        exists_chk = path.exists(output_tab_folder) and path.isdir(output_tab_folder)
        if exists_chk:
            csv_cnt_chk = len(listdir(output_tab_folder)) == len(listdir(test_tab_folder))
    else:
        exists_chk = True
        csv_cnt_chk = True
    
    chks_list = [exists_chk, csv_cnt_chk]
    assert chks_list.all()


def test_verify_pvals_csv(inputs_obj, test_datasets):
    output_data_path = path.join(inputs_obj.out_shp_path, "pvals.csv")
    test_data_path = test_datasets[path.basename(output_data_path).split('_')[-1]]

    if not path.exists(output_data_path):
        assert False
    
    output_df = pd.read_csv(output_data_path)
    test_df = pd.read_csv(test_data_path)

    chk = output_df.eq(test_df).all().all()
    assert chk


def test_verify_log(inputs_obj):
    output_log_path = inputs_obj.blabfile
    if inputs_obj.blabfile != '' and inputs_obj.blabber:
        exists_chk = path.exists(output_log_path)
        size_chk = path.getsize(output_log_path) > 0
    else:
        exists_chk = True
        size_chk = True
    chks_list = [exists_chk, size_chk]
    assert chks_list.all()


def test_verify_heatmap_tif(inputs_obj, test_datasets):
    if inputs_obj.use_heatmap:
        output_data_path = path.join(inputs_obj.out_shp_path, f"{inputs_obj.proj_prefix}_{inputs_obj.hm_name}.tif")
        test_data_path = test_datasets['heatmap.tif']

        exists_chk = path.exists(output_data_path)
        size_chk = path.getsize(output_data_path) > 0

        with rasterio.open(output_data_path, 'r') as ras:
            output_hm_vals = ras.read(1)
            output_hm_ul_xy = ras.transform * (0,0)
            output_hm_lr_xy = ras.transform * (ras.width, ras.height)
        
        with rasterio.open(test_data_path, 'r') as ras:
            test_hm_vals = ras.read(1)
            test_hm_ul_xy = ras.transform * (0,0)
            test_hm_lr_xy = ras.transform * (ras.width, ras.height)
        
        ul_xy_chk = output_hm_ul_xy == test_hm_ul_xy
        lr_xy_chk = output_hm_lr_xy == test_hm_lr_xy
        val_chk = np.equal(output_hm_vals, test_hm_vals).all()
        chks_list = [exists_chk, size_chk, ul_xy_chk, lr_xy_chk, val_chk]
        assert chks_list.all()
    else:
        assert True

    
