import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #Create Sample Data for goldsmith, CO
    __Purpose:__
    This notbook creates sample data for goldsmith, CO. It takes 4 Grids (GG_100yr_Depth_05ft.tif', GG_100yr_Duration_hrs_05ft.tif, GG_100yr_Vel_Max_01ft.tif, and GG_100yr_Vel_Max_05ft.tif), clips, resamples, and reprojects them to WGS84. Each raster should be approximately 25 MB. The notebook then extracts NSI data within the extent of the exported rasters and exports them to a GeoParquet file.
    __Core Technologies Used:__
    - `rasterio`: A geospatial library for the reading, writing, and maipulation of raster data. It is used here to provide input/output functionallity for raster data, as well as performing other spatial operations, namely reprojection, resampling, and clipping.
    - `Shapely`: A library for creating geometry objects, such as points, lines, and polygons. It is used here to create a mask to extract point data with.
    - `geopandas`: An extension of the data manipulation library pandas that adds functionality for spatial data and operations. It is used to extract the NSI points within the bounds of the rasters into a geodataframe before exporting them to a GeoParquet. Note that in order for Geopandas to export files as a GeoParquet, `pyarrow` must be installed as a dependancy.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##1) Configuration
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    __Overview__:
    1. Import modules.
    2. Define folder structure, input paths, and output paths.
    3. Define bounding box properties and CRSs.
    """)
    return


@app.cell
def import_modules():
    # import modules
    import marimo as mo
    from os import path as pth, listdir, mkdir, remove
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from shapely import box, ops
    import geopandas as gpd
    from pyproj import Transformer
    return (
        Resampling,
        Transformer,
        box,
        calculate_default_transform,
        gpd,
        listdir,
        mkdir,
        mo,
        ops,
        pth,
        rasterio,
        remove,
        reproject,
    )


@app.cell
def folder_structure(mkdir, pth):
    # define folder structure
    in_data_dir = r'C:\inland-consequences-goldsmith-data'
    out_data_dir = r'C:\inland-consequences\examples\goldsmith_co_hazard_data'

    temp_dir = pth.join(out_data_dir, 'temp') # used to store reprojected rasters before they're clipped
    if not pth.exists(temp_dir):
        mkdir(temp_dir)
    return in_data_dir, out_data_dir, temp_dir


@app.cell
def in_file_paths(in_data_dir, pth):
    # define input dataset paths
    _in_raster_file_names = ['GG_100yr_Depth_05ft.tif', 
                            'GG_100yr_Duration(hrs)_05ft.tif', 
                            'GG_100yr_Vel(Max)_01ft.tif', 
                            'GG_100yr_Vel(Max)_05ft.tif']
    in_raster_paths = [pth.join(in_data_dir, _f) for _f in _in_raster_file_names]

    in_nsi_file_name = 'nsi_2022_08.gpkg'
    in_nsi_pth = pth.join(in_data_dir, in_nsi_file_name)
    return in_nsi_file_name, in_nsi_pth, in_raster_paths


@app.cell
def out_file_paths(in_nsi_file_name, out_data_dir, pth):
    # define output data paths
    _out_raster_file_names = ['GG_100yr_Depth_05ft.tif', 
                            'GG_100yr_Duration_hrs_05ft.tif', 
                            'GG_100yr_Vel_Max_01ft.tif', 
                            'GG_100yr_Vel_Max_05ft.tif']
    out_clipped_raster_paths = [pth.join(out_data_dir, _f) for _f in _out_raster_file_names]
    out_wgs84_raster_paths = [pth.join(out_data_dir, _f.split('.')[0]+'_wgs84.tif') for _f in _out_raster_file_names]

    _out_nsi_file_name = in_nsi_file_name.split('.')[0] + '_subset.parquet'
    out_nsi_parquet = pth.join(out_data_dir, _out_nsi_file_name)
    return out_clipped_raster_paths, out_nsi_parquet, out_wgs84_raster_paths


@app.cell
def bbox_and_crs_values():
    # define crs
    raster_crs = "EPSG:2877" # NAD83(HARN)/Colorado Central (ftUS) - input raster crs
    intermediate_crs = "EPSG:4759" # NAD83(NSRS2007)
    nsi_crs = "EPSG:4326" # WGS84 - output crs

    # define bounding box lower left xy & dimensions
    # width*height = 6,553,600, which is exactly the number of 32 bit cells in 25 MB.
    bbox_width_cells = 2560
    bbox_height_cells = 2560

    ll_x = 3_165_489.15
    ll_y = 1_658_132.63
    return (
        bbox_height_cells,
        bbox_width_cells,
        intermediate_crs,
        ll_x,
        ll_y,
        nsi_crs,
        raster_crs,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##2) Process Rasters
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    __Overview__:
    1. Clips each raster down and exports it as a new GeoTiff. The first raster processed is used to deterime the upper-right X and Y coordinated for the bounding box of the clipping extent.
    2. Reprojects and resamples the clipped rasters to new geotiffs in NSI's CRS (should be WGS84). An intermediate projection is needed between the original raster CRS and WGS84, so temporary reprojected rasters are created in a 'temp' folder.
    3. Deletes temporary reprojected rasters from 'temp' folder.

      __Note__: This section _must_ be run before any point data is processed, as the upper-right X and Y coordinates for the bounding box are defined here.
    """)
    return


@app.cell
def clip_rasters(
    bbox_height_cells,
    bbox_width_cells,
    in_raster_paths,
    ll_x,
    ll_y,
    out_clipped_raster_paths,
    rasterio,
):
    _first_pass = True
    _path_pairs = list(zip(in_raster_paths, out_clipped_raster_paths))

    for _in_path, _out_path in _path_pairs:
        with rasterio.open(_in_path) as _src:
            # use the first raster to determine the upper right XY coords for the bounding box
            if _first_pass:
                _cell_size_x = _src.transform[0]
                _cell_size_y = abs(_src.transform[4])

                ur_x = ll_x + (bbox_width_cells * _cell_size_x) # max X val
                ur_y = ll_y + (bbox_height_cells * _cell_size_y) # max Y val

                _first_pass = False

            # creating window with dimensions of output extent
            _win_start_row, _win_start_col = _src.index(ll_x, ur_y)
            _win_stop_row, _win_stop_col = _src.index(ur_x, ll_y)

            _row_slice = slice(int(_win_start_row), int(_win_stop_row))
            _col_slice = slice(int(_win_start_col), int(_win_stop_col))

            _out_extent = rasterio.windows.Window.from_slices(
                                                rows=_row_slice, 
                                                cols=_col_slice, 
                                                width=bbox_width_cells, 
                                                height=bbox_height_cells
                                                )

            # extract cells within window as np array and output it to a GeoTiff
            _subset = _src.read(1, window=_out_extent)
            _out_ras = rasterio.open(_out_path, 
                            'w+', 
                            driver='GTiff', 
                            height=_subset.shape[0], 
                            width=_subset.shape[1], 
                            count=1, 
                            dtype=_subset.dtype, 
                            nodata=_src.nodata, 
                            crs=_src.crs, 
                            transform=_src.window_transform(_out_extent))

            _out_ras.write(_subset, 1)
            _out_ras.close()
    return ur_x, ur_y


@app.cell
def project_rasters(
    Resampling,
    calculate_default_transform,
    intermediate_crs,
    listdir,
    nsi_crs,
    out_clipped_raster_paths,
    out_wgs84_raster_paths,
    pth,
    rasterio,
    remove,
    reproject,
    temp_dir,
):
    _path_pairs = list(zip(out_clipped_raster_paths, out_wgs84_raster_paths))

    for _in_path, _out_path in _path_pairs:
        # create path for temp intermediate projected raster
        _temp_path = pth.join(temp_dir, 'temp_'+pth.basename(_in_path))

        # calculate transform for projection from EPSG:2877 to EPSG:4759
        with rasterio.open(_in_path) as _src:
            _temp_transform, _temp_width, _temp_height = calculate_default_transform(
                _src.crs, 
                intermediate_crs,
                _src.width, 
                _src.height, 
                *_src.bounds
            )

            _kwargs= _src.meta.copy()
            _kwargs.update({
                'crs':intermediate_crs,
                'transform':_temp_transform,
                'width':_temp_width,
                'height':_temp_height
            })

            # project clipped raster to new temp dataset
            _temp = rasterio.open(_temp_path, 'w+', **_kwargs)
            reproject(
                source=rasterio.band(_src, 1),
                destination=rasterio.band(_temp, 1),
                src_transform=_src.transform,
                src_crs=_src.crs,
                dst_transform=_temp_transform,
                dst_crs=intermediate_crs,
                resampling=Resampling.cubic 
            )

        # calculate transform for projection from EPSG:4759 to EPSG:4326
        _wgs_transform, _wgs_width, _wgs_height = calculate_default_transform(
                _temp.crs, 
                nsi_crs,
                _temp.width, 
                _temp.height, 
                *_temp.bounds
            )
    
        _kwargs= _temp.meta.copy()
        _kwargs.update({
                'crs':nsi_crs,
                'transform':_wgs_transform,
                'width':_wgs_width,
                'height':_wgs_height
        })

        # project temp raster to output wgs84 raster
        with rasterio.open(_out_path, 'w', **_kwargs) as _out_ras:
            reproject(
                source=rasterio.band(_temp, 1),
                destination=rasterio.band(_out_ras, 1),
                src_transform=_temp.transform,
                src_crs=_temp.crs,
                dst_transform=_wgs_transform,
                dst_crs=nsi_crs,
                resampling=Resampling.cubic
            )

        _temp.close()

    # delete temp rasters
    for _f in [pth.join(temp_dir, _basename) for _basename in listdir(temp_dir)]:
        print(f"Deleting {_f}...")
        remove(_f)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ##3) Process NSI Point Data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    __Overview__:
    1. Creates bounding box to define the extent of the output GeoParquet and properly projects it into WGS84.
    2. Brings NSI data in as a GeoDataframe masked by the bounding box.
    3. Exports the features in the GeoDataframe as a GeoParquet.

      __Note__: Section 2 of this notebook _must_ be run before any point data is processed, as the upper-right X and Y coordinates for the bounding box are defined there.
    """)
    return


@app.cell
def create_bbox(
    Transformer,
    box,
    intermediate_crs,
    ll_x,
    ll_y,
    nsi_crs,
    ops,
    raster_crs,
    ur_x,
    ur_y,
):
    # create bounding box to extract nsi points
    _bbox = box(ll_x, ll_y, ur_x, ur_y)

    # create transformers
    _nad_to_nad_transform = Transformer.from_crs(raster_crs, intermediate_crs, always_xy=True).transform
    _nad_to_wgs_transform = Transformer.from_crs(intermediate_crs, nsi_crs, always_xy=True).transform

    # reproject bbox
    _temp_bbox = ops.transform(_nad_to_nad_transform, _bbox)
    wgs84_bbox = ops.transform(_nad_to_wgs_transform, _temp_bbox)
    return (wgs84_bbox,)


@app.cell
def extract_nsi_points(gpd, in_nsi_pth, out_nsi_parquet, wgs84_bbox):
    # use geopandas to extract nsi points within bbox to a geoparquet
    _gdf = gpd.read_file(in_nsi_pth, mask=wgs84_bbox)
    _gdf.to_parquet(out_nsi_parquet, compression='zstd', geometry_encoding='WKB', schema_version='1.0.0') # requires pyarrow as a dependancy
    return


if __name__ == "__main__":
    app.run()
