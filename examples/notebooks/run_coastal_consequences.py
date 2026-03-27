import marimo

__generated_with = "0.20.3"
app = marimo.App(width="medium")

with app.setup(hide_code=True):
    # impoort modules
    import marimo as mo
    from inland_consequences.coastal import pfracoastal
    import os
    import rasterio
    import matplotlib.pyplot as plt

    # define strings to render tables in markdown
    building_table="""
    | Field name | Type | Description | Default |  
    |:------------|:----------|:-------------------------------------------------------------------------------------------------------------------|:--------|  
    | location | String | Building id, can be NULL | -1 |  
    | BLDG_DED | Integer | Building insurance deductible | 2000 |  
    | BLDG_LIMIT | Integer | Building insurance limit | 200000 |  
    | CNT_DED | Integer | Contents insurance deductible | 1000 |  
    | CNT_LIMIT | Integer | Contents insurance limit | 100000 |  
    | BLDG_VALUE | Integer | Building replacement cost ($) | 200000 |  
    | CNT_VALUE | Integer | Contents replacement cost ($) | 100000 |  
    | NUM_STORIE | Integer | Number of stories | 1 |  
    | foundation | Integer | foundation	Numeric	Foundation type, (2 = basement; 4 = crawlspace; 6 = pier; 7 = fill or wall; 8 = slab; 9 = pile) | 8 |  
    | BasementFi | Integer | Basement Finish type, (0 = no basement; 1 = unfinished basement; 2 = finished basement) | 0 |
    | FIRST_FLOO | Integer | First floor height (feet above ground) | 1 |  
    | DEMft | Float | Digital Elevation Model (DEM) (ground) elevation (feet NAVD88) | -9999 |
    """

    surge_wave_table="""
    | Field Name | Type | Description |  
    |:------------|:----------|:------------------------------------------------------------------|  
    | AID | Integer | Unique Node ID |  
    | e1 | Float | estimated SWEL for the 0.1 annual-chance event (feet NAVD88) |  
    | e2 | Float | estimated SWEL for the 0.05 annual-chance event (feet NAVD88) |  
    | e5 | Float | estimated SWEL for the 0.0333 annual-chance event (feet NAVD88) |  
    | e10 | Float | estimated SWEL for the 0.025 annual-chance event (feet NAVD88) |  
    | e20 | Float | estimated SWEL for the 0.02 annual-chance event (feet NAVD88) |  
    | e50 | Float | estimated SWEL for the 0.0167 annual-chance event (feet NAVD88) |  
    | e100 | Float | estimated SWEL for the 0.0143 annual-chance event (feet NAVD88) |  
    | e200 | Float | estimated SWEL for the 0.0125 annual-chance event (feet NAVD88) |  
    | e500 | Float | estimated SWEL for the 0.01111 annual-chance event (feet NAVD88) |  
    | e1000 | Float | estimated SWEL for the 0.01 annual-chance event (feet NAVD88) |  
    | e2000 | Float | estimated SWEL for the 0.005 annual-chance event (feet NAVD88) |  
    | e5000 | Float | estimated SWEL for the 0.0033 annual-chance event (feet NAVD88) |  
    | e10000 | Float | estimated SWEL for the 0.0025 annual-chance event (feet NAVD88) |  
    """

    ddf_table = """
    | Field name | Type | Description |  
    |:-------------|:----------|:-----------------------------------------------------|  
    | BldgDmgFnID | Integer | Building Function ID, unique |  
    | m4 | Integer | Damage (%) taken at -4 feet of flood depth |  
    | m3 | Integer | Damage (%) taken at -3 feet of flood depth |  
    | m2 | Integer | Damage (%) taken at -2 feet of flood depth |  
    | m1 | Integer | Damage (%) taken at -1 feet of flood depth |  
    | p0 | Integer | Damage (%) taken at 0 feet of flood depth |  
    | p1 | Integer | Damage (%) taken at +1 feet of flood depth |  
    | p2 | Integer | Damage (%) taken at +2 feet of flood depth |  
    | p3 | Integer | Damage (%) taken at +3 feet of flood depth |  
    | p4 | Integer | Damage (%) taken at +4 feet of flood depth |  
    | p5 | Integer | Damage (%) taken at +5 feet of flood depth |  
    | p6 | Integer | Damage (%) taken at +6 feet of flood depth |    
    | p7 | Integer | Damage (%) taken at +7 feet of flood depth |    
    | p8 | Integer | Damage (%) taken at +8 feet of flood depth |    
    | p9 | Integer | Damage (%) taken at +9 feet of flood depth |    
    | p10 | Integer | Damage (%) taken at +10 feet of flood depth |  
    | p11 | Integer | Damage (%) taken at +11 feet of flood depth |  
    | p12 | Integer | Damage (%) taken at +12 feet of flood depth |  
    | p13 | Integer | Damage (%) taken at +13 feet of flood depth |  
    | p14 | Integer | Damage (%) taken at +14 feet of flood depth |  
    | p15 | Integer | Damage (%) taken at +15 feet of flood depth |  
    | p16 | Integer | Damage (%) taken at +16 feet of flood depth |
    """


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Coastal Consequences Analysis Example Notebook
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    The `runPFRAcoastal()` method in `inland_consequences.coastal` calculates Average Annualized Losses (AAL) with uncertainty for coastal Future of Flood Risk Data (FFRD). Originally written in R, the function takes in buildings data, as well as coastal surge and wave model data, to calculate AAL at three-error class intervals (low, best estimate, and high) per structure in the buildings dataset.

    This notebook provides an example of how to run coastal analysis using the `coastal` submodule of the `inland_consequences` module. It is not meant to be used as an application in and of itself.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Input Dataset Requirements
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    Note: All of the spatial datasets (buildings, surge, and wave) must be ESRI shapefiles in the same Coordinated Reference System (CRS) that uses U.S. feet as its linear unit.

    See the project documentation for more information.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Buildings
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    The buildings dataset should have point features that each represent a single family residential structure. It also must have the following attributes:  
    {building_table}
    If missing values are encountered, they will be replaced with the shown default. If a field is not found, it will be created and populated with the default value. If the provided building dataset does not have attribute values with the required field names, a user can re-map the required field names to match the input values using the 'GCB_' parameters in the inputs object.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    ### Surge & Wave
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    __Surge__: The surge elevation dataset should ideally be obtained from the North Atlantic Coast Comprehensive Study (NACCS). Two of tables are required to be extraced from it: the probabilistic-Q SWL, Best Estimate (BE) table and the 84% Confidence Limit (CL) table. Surge elevation, including wave setup, in both datasets needs to be recalculated in feet (NAVD88) instead of meters.
    Additionally, each table needs to be joined to its respective data node location table, using row number as the unique join field. Every node location must be represented in both datasets with the same unique node ID refereing to the same node location in both datasets.    

    __Waves__: The wave height dataset should ideally be obtained from the North Atlantic Coast Comprehensive Study (NACCS). Two of tables are required to be extraced from it: the probabilistic-Q Significant Wave Height (Hm0) table and the COND 84% CL table. The wave height in both datasets needs to be converted from significant wave height, measured in meters, to controling wave height, measured in feet (NAVD88), by multiplying it by 1.6. Additionally, each table needs to be joined to its respective data node location table, using row number as the unique join field. Every node location must be represented in both datasets with the same unique node ID refereing to the same node location in both datasets. 

    __Both Surge & Wave Datasets Need to Have The Following Fields:__  
    {surge_wave_table}  
    Note: The data fields above describe wave height for the wave datasets.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Building Depth Damage Table
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(rf"""
    Must be a csv file with the following fields:  
    {ddf_table}
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ### Storm Suite (Optional)
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    A storm suite is a list of N probabilities between 0.0001 and 1 that are converted to event probabilities and are used to calculate damages and losses for each building. The recommended and default value for N is 2000. This is an optional dataset to include because the analysis automatically generates a random sample of N probabilities if a predefined storm suite is not provided as an input.

    A predefined storm suite must be a csv file that has a single values column with a header of any name. All the values in this column should be in decimal form and have a minimum of 5 decimal places. Additionally, the values may be unsorted.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Set Input Parameters & Create Output Directory
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    The following folder paths are defaults meant to work within the original folder structure of the inland_consequences repository. If different data or folders need to be accessed, the paths defined in the cell below can be altered.
    """)
    return


@app.cell
def define_folder_structure():
    # get directories with test data
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    coastal_dir = os.path.join(root_dir, 'src', 'inland_consequences', 'coastal')

    _test_data_dir = os.path.join(coastal_dir, 'tests', '_data', 'TEST_CALC')
    test_data_dir_input = os.path.join(_test_data_dir, 'input')
    test_data_dir_output = os.path.join(_test_data_dir, 'output') # not the output directory for this notebook
    return coastal_dir, root_dir, test_data_dir_input, test_data_dir_output


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    The following cell has the parameters that will be used as inputs to the coastal analysis function. Although they've all been set with default values, you can modify any of the paths to point to your data as needed.

    The non-boolean, uncommented variables that store paths to datasets are the only ones that need to be explicitly set with a value. The only exception to this is `in_storm_csv`, as the tool will generate one from a smaple of random values if one is not provided by the user.

    The variables that have been commented out are left as their default values in the tool's `Inputs` object for the purposes of this example notebook. They should generally be left commented out and unused, unless specifically needed.
    """)
    return


@app.cell
def set_paramerter_values(
    coastal_dir,
    root_dir,
    test_data_dir_input,
    test_data_dir_output,
):
    _bldg_basename = "Calc_bldg_sample.shp"
    in_bldg_path = os.path.join(test_data_dir_input, _bldg_basename) # Path to building point shapefile

    _swelA_basename = "Calc_SWL_BE_sample.shp"
    in_swelA_path = os.path.join(test_data_dir_input, _swelA_basename) # Path to surge (Best Estimate) point shapefile

    _swelB_basename = "Calc_SWL_84_sample.shp"
    in_swelB_path = os.path.join(test_data_dir_input, _swelB_basename) # Path to surge (84% Confidence Limit) point shapefile.

    _waveA_basename = "Calc_Hc_BE_sample.shp"
    in_waveA_path = os.path.join(test_data_dir_input, _waveA_basename) # Path to wave height (Best Estimate) point shapefile.

    _waveB_basename = "Calc_Hc_84_sample.shp"
    in_waveB_path = os.path.join(test_data_dir_input, _waveB_basename) # Path to wave height (84% Confidence Limit) point shapefile.

    _bddf_lut_basename = "Building_DDF_LUT_CPFRAworking.csv"
    in_bddf_lut_path = os.path.join(coastal_dir, _bddf_lut_basename) # Path to building damage function CSV file.

    _storm_csv_basename = "pvals.csv"
    in_storm_csv = os.path.join(test_data_dir_output, _storm_csv_basename) # Path to CSV file containing an existing Monte Carlo storm suite to use instead of generating a new one.

    in_proj_prefix = "CoastalAnalysisExample" # A text prefix to prepend to the names of all output files.

    _out_dir_name = "coastal_outputs"
    in_out_shp_path = os.path.join(root_dir, _out_dir_name) # Path to a directory where all output files will be saved.

    in_blabber = True # Whether to lib.write_log log messages to console and disk.
    in_use_heatmap = True # Whether to generate a GeoTIF heatmap of building losses.
    in_use_outcsv = True # Whether to output intermediate loss tables for each building as CSV files.

    #in_hm_bandwidth=1100 # Search radius for points used during heatmap generation.      
    #in_hm_resolution=500 # Raster resolution used during heatmap generation.      
    #in_hm_name="heatmap" # Name for the heatmap output file (minus extension).

    #in_mc_n=2000 # Number of storms to use when generating the Monte Carlo storm suite.                 
    #in_nbounds=tuple([0.0001, 1])  # Upper and lower bounds for the probability distribution function used to generate a Monte Carlo storm suite.

    #in_bldg_lay=None # Not used.          
    #in_swel_mpath='' # Not used.
    #in_swel_path='' # Not used.                          

    #in_use_uncertainty=True # Whether to include uncertainty in the analysis. This value should always be set to "True" as the model always assumes uncertainty is applied.

    #in_use_cutoff=True # Whether to apply a cutoff to the damage function. This value should always be set to "True" as the model always assumes a cutoff is applied.

    #in_use_cutoff10=False # Whether to apply a cutoff at 10% damage. This value should always be set to "False" as the model does not assume a 10% cutoff is applied.

    #in_use_eWet=True # Whether to include minimum wetting in the analysis. This value should always be set to "True" as the model assumes no damage when ground is dry.

    #in_use_waves=True # Whether to include wave shapefiles in the analysis. This value should always be set to "True" as the model always assumes wave data is present.

    #in_use_twl=False # Whether to include total water level in the analysis. This value should always be set to "False" as the model always generates a TWL instead of assuming one is provided.

    #in_use_wavecut50=False # Whether to apply a wave cutoff at 50% damage. This value should always be set to "False" as the model does not assume a 50% wave cutoff is applied.

    #in_use_erosion=False # Whether to include erosion effects in the analysis. This value should always be set to "False" as the model does not assume that erosion is included.

    #in_use_insurance=False # Whether to adjust losses in the analysis based on insurance deductibles and limits. This value should always be set to "False" as the model does not currently support this feature.

    #in_use_contents=False # Whether to include contents damage in the analysis. This value should always be set to "False" as the model does not currently support this feature.

    #in_use_netcdf=False # Not used.                     

    #in_bldg_ddf_lut=None # Building damage function lookup table stored in a pandas DataFrame. This is set automatically by the bddf_lut_path setter and should not be set directly.         

    #in_cddf_lut_path=None # Path to contents damage function CSV file. This value should always be set to "None" or an empty string as the model does not currently support contents damage.

    #in_cont_ddf_lut=None # Contents damage function lookup table as a pandas DataFrame. This is set automatically by the cddf_lut_path setter and should not be set directly.          

    #in_GCB_fid="location" # Field name in the building shapefile that contains the unique building identifier. Required.       
    #in_GCB_Bded="BLDG_DED" # Field name for building insurance deductible in the building shapefile.       
    #in_GCB_Blim="BLDG_LIMIT" # Field name for building insurance limit in the building shapefile.     
    #in_GCB_Bval="BLDG_VALUE" # Field name for building replacement cost in the building shapefile. Required.     
    #in_GCB_Cded="CNT_DED" # Field name for contents insurance deductible in the building shapefile.        
    #in_GCB_Clim="CNT_LIM" # Field name for contents insurance limit in the building shapefile.        
    #in_GCB_Cval="CNT_VALUE" # Field name for contents replacement cost in the building shapefile.
    #in_GCB_Bsto="NUM_STORIE" # Field name for number of stories in the building shapefile. Required.     
    #in_GCB_Bfou="foundation" # Field name for foundation type in the building shapefile. Required.   
    #in_GCB_Bbfi="BasementFi" # Field name for basement finish type in the building shapefile. Required.   
    #in_GCB_Bffh="FIRST_FLOO" # Field name for first floor height in the building shapefile. Required.     
    #in_GCB_Bdem="DEMft" # Field name for ground elevation in the building shapefile. Required. 
    return (
        in_bddf_lut_path,
        in_blabber,
        in_bldg_path,
        in_out_shp_path,
        in_proj_prefix,
        in_storm_csv,
        in_swelA_path,
        in_swelB_path,
        in_use_heatmap,
        in_use_outcsv,
        in_waveA_path,
        in_waveB_path,
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    __Note__: The output folder for the output files needs to have been created before the analysis is run.
    """)
    return


@app.cell
def construct_inputs_object(
    in_bddf_lut_path,
    in_blabber,
    in_bldg_path,
    in_out_shp_path,
    in_proj_prefix,
    in_storm_csv,
    in_swelA_path,
    in_swelB_path,
    in_use_heatmap,
    in_use_outcsv,
    in_waveA_path,
    in_waveB_path,
):
    # create Inputs() object
    inputs = pfracoastal.Inputs(
        blabber=in_blabber,
        use_heatmap=in_use_heatmap,
        bldg_path=in_bldg_path,
        swelA_path=in_swelA_path,
        swelB_path=in_swelB_path,
        waveA_path=in_waveA_path,
        waveB_path=in_waveB_path,
        bddf_lut_path=in_bddf_lut_path,
        storm_csv=in_storm_csv,
        proj_prefix=in_proj_prefix,
        out_shp_path=in_out_shp_path,
        use_outcsv=in_use_outcsv)

    # create the output directory if it doesn't already exist
    if not os.path.exists(inputs.out_shp_path):
        os.mkdir(inputs.out_shp_path)
    return (inputs,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Run Analysis
    """)
    return


@app.cell
def run_analysis(inputs):
    _pfra = pfracoastal.PFRACoastal()
    _pfra.runPFRACoastal(inputs)
    return


@app.cell(hide_code=True)
def _(inputs):
    mo.md(rf"""
    Output files will be witten to the following directory:  
    {inputs.out_shp_path}
    """)
    return


@app.cell
def visualize_heatmap(inputs):
    # visualize output heatmap (if one was generated)
    _out_hm_path = os.path.join(inputs.out_shp_path, f"{inputs.proj_prefix}_{inputs.hm_name}.tif")

    _fig, _ax = plt.subplots(1)
    _ax.tick_params(left=False, bottom=False)
    _ax.tick_params(axis='x', labelbottom=False)
    _ax.tick_params(axis='y', labelleft=False)

    _cmap = 'Blues_r' # name of a matplotlib color ramp

    if os.path.exists(_out_hm_path):
        with rasterio.open(_out_hm_path) as _hm:
            plt.imshow(_hm.read(1), cmap=_cmap)
            plt.colorbar(label="AAL in $ per Acre")
            plt.show()
    return


if __name__ == "__main__":
    app.run()
