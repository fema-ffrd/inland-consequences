import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # Outstanding:
    1. Download data from GitHub or expect it to be local? Alternatively, could/should we create a data module that is pip-installable?
    2. Resolve NSI id field (hardcoded as target_fid, but appears to be fd_id in example data) - use fd_id (public)
    3. Build out the InlandFloodVulnerability class (inland_vulnerability.py) and transfer logic from inland_flood_analysis.py. Includes updating default lookup_table_dir definition.
    4. Add aggregated_results
    5. Export_wide?
    6. Export to parquet for GIS: https://github.com/Niyam-Projects/sphere/blob/feat/tsunami/examples/ttf-tsunami.py
    7. Results: https://mbakerintl.sharepoint.com/:w:/r/sites/PTS3SO1Innovations/Shared%20Documents/SO3.1%20Projects/Inland%20Consequences%20Method/Task%206%20Agile%20Prototyping/Documentation/Results%20Design%20Summary.docx?d=w12edc408ff5e4bf09095336d1deb6257&csf=1&web=1&e=gl3ydh
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    # Inland Consequences - Single Return Period Run
    This notebook demonstrates the use of the FEMA Inland Consequences Tool to produce damage estimates for a single return period flood event in the Goldsmith Gulch area of Denver, Colorado.

    The process follows these steps:
    1. Read the sample data from the [project repository]("https://github.com/fema-ffrd/inland-consequences") and view the contents
    2. Perform consequence estimation for the 100-year event using only the depth grid.
    3. Explore the results in tabular and spatial form
    4. Export the data to a format of your choice.
    """)
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Read the sample NSI data
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    **Read the example data locally**

    The example data for this notebook is located in the `goldsmith_co_hazard_data/` subfolder relative to this notebook. The data includes:
    - NSI (National Structure Inventory) building data
    - 100-year flood depth and velocity grids

    _Note: If you don't have the example data, clone the repository from [GitHub](https://github.com/fema-ffrd/inland-consequences) and follow the setup instructions in the [README](https://github.com/fema-ffrd/inland-consequences#readme)._
    """)
    return


@app.cell
def _():
    import os
    import geopandas as gpd

    # get the location of this notebook
    notebooks_dir = os.path.dirname(os.path.abspath(__file__))
    sample_data_path = os.path.abspath(os.path.join(notebooks_dir, 'goldsmith_co_hazard_data'))

    nsi_path = os.path.join(sample_data_path, "nsi_2022_08_subset.parquet")

    # read National Structure Inventory (NSI) data and view a sample of the data
    gdf = gpd.read_parquet(nsi_path)

    gdf['target_fid'] = gdf['fd_id'] # TODO - resolve which field is expected (it appears fd_id, but our code says target_fid)
    gdf.sample(10)
    return gdf, gpd, os, sample_data_path


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Run the analysis with the 100-year depth
    """)
    return


@app.cell
def _():
    import time
    from inland_consequences.nsi_buildings import NsiBuildings
    from inland_consequences.inland_vulnerability import InlandFloodVulnerability
    from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
    from inland_consequences.raster_collection import RasterCollection
    from sphere.flood.single_value_reader import SingleValueRaster

    return (
        InlandFloodAnalysis,
        InlandFloodVulnerability,
        NsiBuildings,
        RasterCollection,
        SingleValueRaster,
    )


@app.cell
def _(mo):
    mo.md(r"""
    **Raster Collections**

    A `RasterCollection` organizes and validates raster data (hazard inputs like flood depth, uncertainty, velocity, and duration) by return period.

    *What is a RasterCollection?*

    A RasterCollection is a wrapper that normalizes hazard inputs across different flood probabilities. Instead of managing separate raster objects, you package them together organized by return period (e.g., 10-year, 100-year, 500-year flood events). This ensures consistent data structure and enables the analysis functions to access hazard values for any return period.

    *How to define one*

    Create a RasterCollection by passing a dictionary with return periods as keys and raster data as values. First, wrap your raster files in `SingleValueRaster` instances, then pass them to RasterCollection:

    ```python
    # First, wrap raster files in SingleValueRaster
    depth_raster = SingleValueRaster(path_to_depth_tif)
    velocity_raster = SingleValueRaster(path_to_velocity_tif)

    # Then create the RasterCollection
    raster_collection = RasterCollection({
        return_period: {
            "depth": depth_raster,              # Required: flood depth
            "uncertainty": uncertainty_value,   # Optional: std dev or raster
            "velocity": velocity_raster,        # Optional: flood velocity
            "duration": duration_raster         # Optional: flood duration
        }
    })
    ```

    - **return_period** (int): The flood return period (e.g., 100 for a 100-year event)
    - **depth** (required): A `SingleValueRaster` instance containing flood depths at each location
    - **uncertainty** (optional): A single numeric value (e.g., 0.2) OR a `SingleValueRaster` instance
    - **velocity, duration** (optional): `SingleValueRaster` instances if provided

    *How it's used*

    The RasterCollection is passed to analysis functions that sample hazard values for buildings at specific locations. For each building, the analysis retrieves the corresponding depth, uncertainty, velocity, and duration values from the rasters at that building's coordinates for the specified return period.
    """)
    return


@app.cell
def _(RasterCollection, SingleValueRaster, os, sample_data_path):
    # setup a SingleValueRaster instance for the 100-year depth and the RasterCollection instance required for analysis
    depth100_tif = os.path.join(sample_data_path, "GG_100yr_Depth_05ft_wgs84.tif")
    depth100 = SingleValueRaster(depth100_tif)
    raster_collection = RasterCollection({
        100: {"depth": depth100}
    })
    return (raster_collection,)


@app.cell
def _(mo):
    mo.md(r"""
    **Building Inventory**

    A building inventory is a GeoDataFrame containing the locations, characteristics, and values of buildings. These attributes—such as occupancy type, foundation type, first-floor height, and replacement cost—are essential for determining vulnerability to flood hazards.

    *Pre-built building inventories*

    The toolkit provides two ready-to-use building inventory classes:

    - **NsiBuildings**: For the National Structure Inventory (NSI) dataset. Handles NSI-specific field names and column mappings automatically.
    - **MillimanBuildings**: For the Milliman dataset. Provides field mappings specific to Milliman data formats.

    Both classes inherit from a base `Buildings` class, which standardizes access to required building attributes (occupancy type, foundation type, cost, etc.) regardless of the source data format.

    *Using a custom building stock*

    If you have your own building data in a different format, you can reference the base `Buildings` class from `sphere.core.schemas.buildings`. Subclass it to define field aliases that map your data columns to the standard building attributes. This ensures compatibility with the analysis pipeline.

    ```python
    from sphere.core.schemas.buildings import Buildings

    class YourCustomBuildings(Buildings):
        def __init__(self, gdf):
            # Define any custom field mappings
            overrides = {"occupancy_type": "your_occupancy_column"}
            super().__init__(gdf, overrides=overrides)
    ```
    """)
    return


@app.cell
def _(NsiBuildings, gdf):
    # Create instance of the NSI Buildings class
    buildings = NsiBuildings(gdf)
    type(buildings)
    return (buildings,)


@app.cell
def _(mo):
    mo.md(r"""
    **Vulnerability**
    Describe what vulnerability is and the components used in loss estimation
    """)
    return


@app.cell
def _(InlandFloodVulnerability, buildings):
    # Create instance of the default inland vulnerability class
    flood_function = InlandFloodVulnerability(buildings)
    type(flood_function)
    return (flood_function,)


@app.cell
def _(mo):
    mo.md(r"""
    **Loss Estimation**

    Loss estimation calculates the expected economic damage to buildings from flood hazards at different return periods. It combines building inventory, flood hazard data (depth, velocity, duration), and vulnerability functions (damage-depth curves) to estimate losses.

    *How it works*

    The loss estimation process follows these steps:

    1. **Damage Function Matching**: Assigns appropriate damage curves (from vulnerability functions) to each building based on attributes like occupancy type, foundation type, story count, and construction material.

    2. **Hazard Sampling**: Extracts flood depth, velocity, duration, and uncertainty values from the raster collection at each building's location for each return period.

    3. **Flood Peril Assignment**: Classifies buildings into flood peril types (e.g., "RLS" for Riverine Low Velocity Short Duration) based on maximum velocity and duration across return periods.

    4. **Interpolation & Uncertainty**: For each building, the damage function curves are interpolated at the flood depth, and adjusted for uncertainty (depth ± standard deviation) to estimate damage mean, min, and max.

    5. **Loss Calculation**: Multiplies the interpolated damage percentages by building replacement costs to estimate dollar losses at each return period.

    6. **AAL Computation** (optional): Integrates losses across all return periods using the trapezoidal rule to compute Annual Average Loss (AAL)—the expected annual loss averaged over many years.

    7. **Validation**: Performs non-fatal checks on building attributes, hazard data consistency, and results to identify potential data quality issues.

    *Running the analysis*

    Create an `InlandFloodAnalysis` instance with your raster collection, buildings, and vulnerability function. Use the context manager (`with analysis:`) to set up a persistent DuckDB database, then call `calculate_losses()`:

    ```python
    from inland_consequences import InlandFloodAnalysis

    analysis = InlandFloodAnalysis(
        raster_collection=raster_collection,
        buildings=buildings,
        vulnerability=flood_vulnerability,
        calculate_aal=True  # Optional: compute Annual Average Loss
    )

    with analysis:
        analysis.calculate_losses()
    ```

    *Results Location*

    All results are stored in a DuckDB database created in the current working directory with a timestamped filename (e.g., `inland_flood_analysis_20260226_091940.duckdb`). Key tables include:

    - **losses**: Building losses by return period (loss_min, loss_mean, loss_std, loss_max)
    - **aal_losses**: Annual Average Loss per building (if `calculate_aal=True`)
    - **buildings**: Input building inventory with assigned flood peril types and validation flags
    - **hazard**: Sampled flood depths, velocities, durations for each building and return period
    - **validation_log**: Non-fatal validation issues identified during processing
    """)
    return


@app.cell
def _(InlandFloodAnalysis, buildings, flood_function, mo, raster_collection):
    with mo.status.spinner(subtitle="Running analysis ...") as _spinner:

        # creating an instance of the analysis class
        analysis = InlandFloodAnalysis(
                    raster_collection=raster_collection,
                    buildings=buildings,
                    vulnerability=flood_function,
                    calculate_aal=True
        )

        # use the context manager to gracefully handle the DuckDB connection used by Inland Consequences
        with analysis:
            # perform the loss estimation
            analysis.calculate_losses()

    type(analysis)
    return (analysis,)


@app.cell
def _(mo):
    mo.md(r"""
    **3. Explore the results**

    Inland consequences performs loss estimation within a DuckDB database which is stored at the root of your project folder.  We can review the results as well as the supporting data by extracting the results to Pandas dataframes.
    """)
    return


@app.cell
def _(analysis):
    import duckdb

    # Get the duckdb database path from the db_path attribute of the analysis class
    db_path = analysis.db_path
    print(f"Results database: {db_path}")

    # Open a connection to analyze results
    conn = duckdb.connect(db_path)
    conn.sql("SHOW TABLES").show()
    return conn, db_path


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Validation**
    The analysis is designed to run even when anomolies in the data are found. The validation_log table is important for users to review to understand data quality and flag issues that may need review and remediation. Here we extract the validation log, show the table, then print the messages and severity levels.
    """)
    return


@app.cell
def _(conn):
    import pandas as pd

    # Extract the validation_log table usig the connection from previous cells
    validation_df = conn.execute("SELECT * FROM validation_log").fetch_df()

    # Display the table in its entirety
    validation_df
    return pd, validation_df


@app.cell
def _(validation_df):
    # Print the unique messages returnd
    print("Validation messages:")
    print(validation_df["message"].unique())
    return


@app.cell
def _(validation_df):
    # print the warning levels to understand severity of issues
    print("Count by Severity:")
    print(validation_df['severity'].value_counts())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **The loss data** can be viewed in the losses table. For multiple return period analyses, the aal table stores the average annualized losses (not present for this single return period analysis).
    """)
    return


@app.cell
def _(conn):
    # Extract the losses table
    losses_df = conn.execute("SELECT * FROM losses").fetch_df()

    # Display the first few rows
    losses_df.head()
    return (losses_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    It's often helpful to join the tabular data back to the original buildings data, convert to a geospatial file, and display on a map or import to your GIS of choice.
    """)
    return


@app.cell
def _(conn, gpd, losses_df, pd):
    # import geopandas as gpd

    # extract buildings
    buildings_df = conn.execute("SELECT * FROM buildings").fetch_df()

    # join buildings to losses by id's
    losses_join_df = pd.merge(losses_df, buildings_df, left_on="id", right_on="fd_id")

    # convert to a geospatial file using geopandas
    losses_join_gdf = gpd.GeoDataFrame(data=losses_join_df, 
                                       geometry=gpd.points_from_xy(losses_join_df.x, losses_join_df.y),
                                       crs="EPSG:4326")
    losses_join_gdf
    return (losses_join_gdf,)


@app.cell
def _(losses_join_gdf):
    import matplotlib.pyplot as plt
    import numpy as np
    from lonboard.colormap import apply_continuous_cmap
    from matplotlib.colors import LinearSegmentedColormap

    _gdf = losses_join_gdf.copy()

    # Use the loss_mean column from the losses table (computed from vulnerability)
    _gdf = _gdf[_gdf['loss_mean'] > 0].copy()

    # Normalize losses for color mapping
    loss_normalized = _gdf['loss_mean'] / _gdf['loss_mean'].max()
    print(f"Loss range: ${_gdf['loss_mean'].min():.2f} to ${_gdf['loss_mean'].max():.2f}")

    # Create a custom colormap
    colors_list = ['blue', 'green', 'yellow', 'red']
    custom_cmap = LinearSegmentedColormap.from_list('custom_cmap', colors_list)

    # Apply power transform for better visual distribution
    stretched_values = loss_normalized ** 0.25
    colors = apply_continuous_cmap(stretched_values.to_numpy(), cmap=custom_cmap)

    from lonboard import Map, ScatterplotLayer

    # Select available columns for display
    # Note: only include columns that exist in the merged dataframe
    available_columns = ['fd_id', 'return_period', 'loss_mean', 'loss_min', 'loss_max', 'geometry']
    columns_to_keep = [col for col in available_columns if col in _gdf.columns]
    _losses = _gdf[columns_to_keep]

    layer = ScatterplotLayer.from_geopandas(
        _losses,
        get_fill_color=colors,
        get_radius=15,
        pickable=True,
    )

    # To see the data, let lonboard handle the view_state automatically
    m = Map(layer)
    m
    return


@app.cell
def _(mo):
    mo.md(r"""
    **4. Exporting Results**
    Results can be exported directly from the duckdb database or after conversion to pandas. This notebook supports several output types:
    - Tabular: Parquet, CSV, Excel (coming soon)
    - Spatial: Geoparquet, Shapefile, ESRI Geodatabase, GeoJSON Geopackage

    Once results are in a Pandas dataframe, exporting single tables is straightforward. However, it's helpful to have each row representa a single buildings and all hazard and loss metrics as columns. Use the `export_wide()` utility to pivot results and export to a location and format of your choice.
    """)
    return


@app.cell
def _(losses_df):
    # export a single table
    losses_df.to_csv("results/losses.csv",)
    return


@app.cell
def _(conn, db_path):
    # use the export_wide utility to get aggregated results by building
    from utils import export_wide, get_database_summary

    # first, ensure any existing connections to the database are closed
    try:
        conn.close()
    except:
        pass

    # Example: export wide format to parquet
    result_gdf, output_path = export_wide(
        db_path=db_path,
        output_path="results/analysis_wide.parquet",
        output_format="parquet",
        include_geometry=True,
        geometry_table="buildings",
        longitude_col="x",
        latitude_col="y"
    )
    return


if __name__ == "__main__":
    app.run()
