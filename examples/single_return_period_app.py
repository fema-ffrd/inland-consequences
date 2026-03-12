import marimo

__generated_with = "0.20.3"
app = marimo.App(width="medium", app_title="Inland Flood Analysis")


@app.cell
def _():
    """Setup: Import all required libraries"""
    import marimo as mo
    import os
    import time
    import geopandas as gpd
    import pandas as pd
    import numpy as np
    import duckdb
    from pathlib import Path

    # Import inland consequences modules
    from inland_consequences.nsi_buildings import NsiBuildings
    from inland_consequences.milliman_buildings import MillimanBuildings
    from inland_consequences.inland_vulnerability import InlandFloodVulnerability
    from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
    from inland_consequences.raster_collection import RasterCollection
    from sphere.flood.single_value_reader import SingleValueRaster

    # Import visualization libraries
    from lonboard import Map, ScatterplotLayer
    from lonboard.colormap import apply_continuous_cmap
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.pyplot as plt
    import altair as alt

    return (
        InlandFloodAnalysis,
        InlandFloodVulnerability,
        LinearSegmentedColormap,
        Map,
        MillimanBuildings,
        NsiBuildings,
        RasterCollection,
        ScatterplotLayer,
        SingleValueRaster,
        alt,
        apply_continuous_cmap,
        duckdb,
        gpd,
        mo,
        os,
        pd,
        time,
    )


@app.cell
def _(mo):
    mo.md("""
    # 🌊 Inland Consequences Solution

    This prototype provides an interactive way to use the PTS Innovations Consequence Solution Python library to calculate inland flood consequences. For detailed methodology and technical implementation documentation, please visit our documentation site. Advanced users can treat this prototype as a reference implementation and extend the base functionality using the library and technical implementation guidance in our documentation.

    /// admonition | Tip
        type: info

    Default paths are pre-filled. Edit them to point to your data files.
    ///


    [Documentation](https://fema-ffrd.github.io/inland-consequences/) | [GitHub](https://github.com/fema-ffrd/inland-consequences)
    """)
    return


@app.cell
def _(mo):
    workflow_diagram = '''
    graph LR
        A[Load Buildings] --> B[Load Hazards]
        B --> C[Sample at Locations]
        C --> D[Match Damage Functions]
        D --> E[Calculate Losses]
        E --> F[AAL Integration]
        F --> G[Export Results]
        style A fill:#ADD8E6
        style B fill:#ADD8E6
        style C fill:#87CEEB
        style D fill:#87CEEB
        style E fill:#4682B4,color:#fff
        style F fill:#90EE90
        style G fill:#DDA0DD
    '''
    mo.accordion({
        " ## 📊 Analysis Workflow": mo.mermaid(workflow_diagram)
    })
    return


@app.cell
def _(mo):
    mo.md("""
    ## Analysis Configuration & Parameters
    """)
    return


@app.cell
def _(mo, os):
    # Get default paths
    default_data_path = os.path.dirname(os.path.abspath(__file__))
    default_output_path = os.path.join(os.path.dirname(default_data_path), 'outputs')

    # # Output directory (text input since it may not exist yet)
    # output_dir_input = mo.ui.text(
    #     value=default_output_path,
    #     label="💾 Output Directory",
    #     placeholder="Path to output directory (will be created)",
    #     full_width=True
    # )

    output_dir_input = mo.ui.file_browser(
        initial_path = default_data_path,
        filetypes = None,
        selection_mode = "directory",
        multiple = False,
        label="💾 Select Output Directory by clicking the folder icon (directory must already exist)",
    )

    select_tip = mo.md("""
    /// admonition | Tip
        type: attention

    Click the **FOLDER ICON** to the **LEFT** of your desired output directory to select it
    ///
        """)
    mo.vstack([
        output_dir_input,
        select_tip

    ])
    return default_data_path, output_dir_input


@app.cell
def _(default_data_path, mo):
    # Building dataset type selector
    building_type_selector = mo.ui.dropdown(
        options=["NSI", "Milliman"],
        value="NSI",
        label="🏢 Building Dataset Type",
    )

    # Building inventory file selector
    building_file_selector = mo.ui.file_browser(
        initial_path=default_data_path,
        filetypes=[".parquet", ".gpkg", ".geojson"],
        label="📁 Building Inventory File (parquet, geopackage, or geojson)",
        multiple=False
    )

    # # Advanced options
    # calculate_aal_checkbox = mo.ui.checkbox(
    #     value=False,
    #     label="Calculate Annual Average Loss (AAL) - requires 3+ return periods"
    # )

    # wildcard_fields_select = mo.ui.multiselect(
    #     options=["foundation_type", "num_stories", "construction_type"],
    #     value=[],
    #     label="Wildcard Fields (ignore in damage function matching)"
    # )

    tip_markdown = mo.md(
        """
    /// admonition | Tip
        type: info

    Advance users can leverage the [technical implementation guidance](https://fema-ffrd.github.io/inland-consequences/building_inventories/#base-buildings-class) to extend the base building class and leverage custom building dataset inputs. 
    ///
        """
    )
    mo.vstack([
        mo.md("## ⚙️ Inventory Configuration"),
        mo.md("Select your building inventory file and configure output settings."),
        building_type_selector,
        building_file_selector,
        tip_markdown,
        # mo.md("### 🔧 Advanced Options"),
        # calculate_aal_checkbox,
        # wildcard_fields_select
    ])
    return building_file_selector, building_type_selector


@app.cell
def _(mo):
    """configure loss calculation method (single, aal (type)"""
    radiogroup = mo.ui.radio(
        options={"Single return period": 1, 
                 "Calculate Standard Non-Truncated  AAL – requires 3+ periods": 3, 
                 "Calculate Truncated Average Annualized Loss AAL – requires 3+ periods  ": 3
                },
        value="Single return period",
        label="pick a number",
    )

    mo.vstack([
        mo.md("## 🌊 Loss Calculation Method Configuration"),
        mo.md("Check the box to select your loss calculation method. See our [technical documentation](https://fema-ffrd.github.io/inland-consequences/AAL_tech_implementation/) for details on Average Annualized Loss (AAL) truncation methods:"),
        radiogroup
    ])
    return (radiogroup,)


@app.cell
def _(mo, radiogroup):
    """Number of Return Periods Selector"""
    if radiogroup.value == 1:
        num_return_periods = mo.ui.number(
            start=1, stop=1, value=1, step=1,
            label="Single return period selected",
            full_width=False
        )
        calculate_aal = False

        _display = mo.vstack([
            mo.md("## :signal_strength: Return Period Configuration"),
            mo.md("You've selected a single return period configuration"),
            mo.md("For the single return period, enter the return period year and select the flood hazard data to use in your analysis. A depth grid is required. Depth uncertainty, velocity, and duration data are optional.")
        ])
    else:
        num_return_periods = mo.ui.number(
            start=3, stop=30, value=3, step=1,
            label="Enter Number of Return Periods (3 or greater)",
            full_width=False
        )
        calculate_aal = True

        _display = mo.vstack([
            mo.md("## :signal_strength: Return Period Configuration"),
            mo.md("**How many return periods do you want to analyze?**"),
            num_return_periods,
            mo.md("For each return period, enter the return period year and select the flood hazard data to use in your analysis. Depth grids are required for every return period. Depth uncertainty, velocity, and duration data are optional.")
        ])

    _display
    return calculate_aal, num_return_periods


@app.cell
def _(default_data_path, mo, num_return_periods, radiogroup):
    """Dynamic Return Period Configurations"""

    # Common return period values for flood modeling
    if radiogroup.value == 1:
        default_rps = [100]
    else:
        default_rps = [
            2, 5, 10, 25, 50, 100, 200, 500, 1000,  # Standard values
        ]

    # Create a batch configuration for each return period
    _rp_configs = []
    for _i in range(num_return_periods.value):
        _default_rp = default_rps[_i] if _i < len(default_rps) else (_i + 1) * 10
        _config = mo.md(
            """
            **Return Period (years):** {return_period}

            **🌊 Depth Raster (required):** {depth_raster}

            **📊 Depth Uncertainty Raster (optional):** {uncertainty_raster}

            **💨 Velocity Raster (optional):** {velocity_raster}

            **⏱️ Duration Raster (optional):** {duration_raster}


            """
        ).batch(
            return_period=mo.ui.number(
                start=1, stop=1000000, value=_default_rp, step=1,
                label="Return Period (years)", full_width=True
            ),
            depth_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Depth Raster",
                multiple=False
            ),
            uncertainty_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Depth Uncertainty Raster",
                multiple=False
            ),
            velocity_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Velocity Raster",
                multiple=False
            ),
            duration_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Duration Raster",
                multiple=False
            ),
        )
        _rp_configs.append(_config)

    # Create accordion sections - first one expanded, rest collapsed
    _accordion_dict = {}
    for _i, _config in enumerate(_rp_configs):
        _label = f"Return Period {_i + 1}" if _i > 0 else f"Return Period {_i + 1} (Required)"
        _accordion_dict[_label] = _config

    rp_configs_list = _rp_configs

    mo.accordion(_accordion_dict)
    return (rp_configs_list,)


@app.cell
def _(mo):
    """Validate Inputs Button"""
    validate_button = mo.ui.run_button(label="✅ Validate Inputs")

    mo.vstack([
        mo.md("---"),
        mo.md("Click the button below to validate your configuration before running analysis:"),
        validate_button
    ])
    return (validate_button,)


@app.cell
def _(
    building_file_selector,
    building_type_selector,
    mo,
    os,
    output_dir_input,
    rp_configs_list,
    validate_button,
):
    """Validate Configuration"""

    # Initialize output variables with defaults
    building_file = None
    building_type = building_type_selector.value
    output_directory = output_dir_input.value
    return_periods_list = []
    raster_config = {}
    config_valid = False

    # Only run validation when button is clicked
    if not validate_button.value:
        _display = mo.callout(
            mo.md("👆 **Click 'Validate Inputs' above** to check your configuration."),
            kind="info"
        )
    else:
        # Collect validation issues
        validation_issues = []

        # Extract building file from file browser
        if len(building_file_selector.value) == 0:
            validation_issues.append("No building file selected. Please select a building inventory file.")
        else:
            building_file = building_file_selector.value[0].path
            if not os.path.isfile(building_file):
                validation_issues.append(f"Building file not found: `{building_file}`")

        # Process each return period configuration
        for _i, _rp_config in enumerate(rp_configs_list):
            _rp_data = _rp_config.value
            _rp = _rp_data["return_period"]

            # Validate depth raster (required)
            if len(_rp_data["depth_raster"]) == 0:
                validation_issues.append(f"No depth raster selected for Return Period {_i + 1}. Depth is required.")
                continue

            _depth = _rp_data["depth_raster"][0].path
            if not os.path.isfile(_depth):
                validation_issues.append(f"Depth raster not found for {_rp}-year: `{_depth}`")
                continue

            return_periods_list.append(_rp)
            raster_config[_rp] = {"depth": _depth}

            # Add optional rasters if provided
            if len(_rp_data["velocity_raster"]) > 0:
                _velocity = _rp_data["velocity_raster"][0].path
                if os.path.isfile(_velocity):
                    raster_config[_rp]["velocity"] = _velocity

            if len(_rp_data["duration_raster"]) > 0:
                _duration = _rp_data["duration_raster"][0].path
                if os.path.isfile(_duration):
                    raster_config[_rp]["duration"] = _duration

            if len(_rp_data["uncertainty_raster"]) > 0:
                _uncertainty = _rp_data["uncertainty_raster"][0].path
                if os.path.isfile(_uncertainty):
                    raster_config[_rp]["uncertainty"] = _uncertainty

        # Determine if configuration is valid
        config_valid = len(validation_issues) == 0 and len(raster_config) > 0

        # Show validation status
        if validation_issues:
            issues_md = "\n".join(f"- {issue}" for issue in validation_issues)
            _display = mo.callout(
                mo.md(f"**Please fix the following issues:**\n\n{issues_md}"),
                kind="danger"
            )
        else:
            _display = mo.callout(
                mo.md(f"✅ **Configuration valid!** {len(return_periods_list)} return period(s) - {return_periods_list}"),
                kind="success"
            )

    _display
    return (
        building_file,
        building_type,
        config_valid,
        output_directory,
        raster_config,
        return_periods_list,
    )


@app.cell
def _(building_file, building_type, calculate_aal, config_valid, mo, os, output_directory, pd, return_periods_list):
    """User Configuration Summary"""
    
    # Only show summary if configuration is valid
    mo.stop(not config_valid, "")
    
    # Extract output directory path from file browser value
    if output_directory and len(output_directory) > 0:
        output_dir_path = str(output_directory[0].path)
    else:
        output_dir_path = "Not selected"
    
    # Build summary data
    summary_data = [
        {"Setting": "Building Dataset Type", "Value": building_type},
        {"Setting": "Building Inventory File", "Value": os.path.basename(building_file)},
        {"Setting": "Output Directory", "Value": output_dir_path},
        {"Setting": "Number of Return Periods", "Value": str(len(return_periods_list))},
        {"Setting": "Return Periods (years)", "Value": ", ".join(str(rp) for rp in return_periods_list)},
        {"Setting": "Calculate AAL", "Value": "Yes" if calculate_aal else "No"},
    ]
    
    summary_df = pd.DataFrame(summary_data)
    
    mo.vstack([
        mo.md("## 📋 Configuration Summary"),
        mo.ui.table(summary_df, selection=None)
    ])
    return


@app.cell
def _(config_valid, mo, pd, raster_config, return_periods_list):
    """Raster Collection Preview"""

    # Only show preview if configuration is valid
    mo.stop(not config_valid, "")

    # Create preview dataframe showing configured rasters
    preview_data = []
    for _rp in return_periods_list:
        _files = raster_config[_rp]
        preview_data.append({
            "Return Period": _rp,
            "Depth": "✅",
            "Velocity": "✅" if "velocity" in _files else "⬜",
            "Duration": "✅" if "duration" in _files else "⬜",
            "Depth Uncertainty": "✅" if "uncertainty" in _files else "⬜"
        })

    preview_df = pd.DataFrame(preview_data)

    mo.vstack([
        mo.md("**📁 Configured Hazard Rasters**"),
        mo.ui.table(preview_df, selection=None)
    ])
    return


@app.cell
def _(mo):
    """Execution Button"""
    run_button = mo.ui.run_button(label="▶️ Run Analysis", kind="success")
    run_button
    return (run_button,)


@app.cell
def _(
    InlandFloodAnalysis,
    InlandFloodVulnerability,
    MillimanBuildings,
    NsiBuildings,
    RasterCollection,
    SingleValueRaster,
    building_file,
    building_type,
    calculate_aal,
    config_valid,
    gpd,
    mo,
    os,
    raster_config,
    return_periods_list,
    run_button,
    time,
):
    """Execute Analysis with Status Tracking"""

    # Require valid configuration and explicit button click
    mo.stop(not config_valid, mo.callout(mo.md("⚠️ Please complete the configuration above before running analysis."), kind="warn"))
    mo.stop(not run_button.value, "")

    start_time = time.perf_counter()
    analysis_results = {}

    # Step 1: Load building inventory
    with mo.status.spinner(title="Loading building inventory..."):
        step_start = time.perf_counter()

        gdf = gpd.read_parquet(building_file)

        # Instantiate the appropriate building class based on selection
        if building_type == "Milliman":
            buildings = MillimanBuildings(gdf)
        else:  # NSI
            # Handle NSI ID field mapping
            if 'fd_id' in gdf.columns and 'target_fid' not in gdf.columns:
                gdf['target_fid'] = gdf['fd_id']
            buildings = NsiBuildings(gdf)

        analysis_results["buildings_loaded"] = len(gdf)
        analysis_results["building_type"] = building_type
        analysis_results["load_time"] = time.perf_counter() - step_start

    # Step 2: Load hazard rasters
    with mo.status.spinner(title="Loading hazard rasters..."):
        step_start = time.perf_counter()
        raster_collection_dict = {}

        for _rp, _files in raster_config.items():
            _rp_dict = {}
            _rp_dict["depth"] = SingleValueRaster(_files["depth"])

            if "velocity" in _files:
                _rp_dict["velocity"] = SingleValueRaster(_files["velocity"])
            if "duration" in _files:
                _rp_dict["duration"] = SingleValueRaster(_files["duration"])
            if "uncertainty" in _files:
                _rp_dict["uncertainty"] = SingleValueRaster(_files["uncertainty"])

            raster_collection_dict[_rp] = _rp_dict

        raster_collection = RasterCollection(raster_collection_dict)
        analysis_results["raster_load_time"] = time.perf_counter() - step_start

    # Step 3: Create vulnerability function
    with mo.status.spinner(title="Initializing vulnerability functions..."):
        step_start = time.perf_counter()
        flood_function = InlandFloodVulnerability(buildings)
        analysis_results["vuln_time"] = time.perf_counter() - step_start

    # Step 4: Run analysis
    with mo.status.spinner(title="Running flood loss analysis...") as spinner:
        step_start = time.perf_counter()

        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection,
            buildings=buildings,
            vulnerability=flood_function,
            calculate_aal=calculate_aal,
            # wildcard_fields=wildcard_fields
        )

        with analysis:
            analysis.calculate_losses()

        analysis_results["analysis_time"] = time.perf_counter() - step_start
        analysis_results["db_path"] = analysis.db_path

    total_time = time.perf_counter() - start_time
    analysis_results["total_time"] = total_time

    mo.callout(
        mo.md(f"""
        ✅ **Analysis Complete!**

        - Building Type: **{analysis_results['building_type']}**
        - Processed **{analysis_results['buildings_loaded']:,}** buildings
        - Analyzed **{len(return_periods_list)}** return period(s)
        - Total time: **{total_time:.1f}s**
        - Results: `{os.path.basename(analysis_results['db_path'])}`
        """),
        kind="success"
    )
    return (analysis_results,)


@app.cell
def _(analysis_results, duckdb, mo):
    """Load Results from Database"""

    # Connect to results database
    db_path = analysis_results["db_path"]
    conn = duckdb.connect(db_path)

    # Load key tables
    # Note: EXCLUDE (geometry) avoids DuckDB -> NumPy conversion error for GEOMETRY columns
    losses_df = conn.execute("SELECT * FROM losses").fetch_df()
    buildings_df = conn.execute("SELECT * EXCLUDE (geometry) FROM buildings").fetch_df()
    validation_df = conn.execute("SELECT * FROM validation_log").fetch_df()

    # Check for AAL table
    tables = conn.execute("SHOW TABLES").fetch_df()
    has_aal = "aal_losses" in tables["name"].values

    if has_aal:
        aal_df = conn.execute("SELECT * FROM aal_losses").fetch_df()
    else:
        aal_df = None

    # Close connection after loading data to avoid conflicts with export
    conn.close()

    # Determine which columns are available in buildings_df
    available_cols = buildings_df.columns.tolist()

    # Build list of columns to use for join, starting with ID
    id_col = None
    for id_candidate in ["fd_id", "target_fid", "id", "building_id", "bldg_id"]:
        if id_candidate in available_cols:
            id_col = id_candidate
            break

    if id_col is None:
        raise ValueError("Could not find ID column in buildings table")

    # Add coordinate columns if available
    join_cols = [id_col]
    for _coord_col in ["x", "y", "longitude", "latitude", "lon", "lat"]:
        if _coord_col in available_cols and _coord_col not in join_cols:
            join_cols.append(_coord_col)

    # Add occupancy column if available
    for _occ_col in ["occtype", "occupancy_type", "occupancy", "occ_type", "building_type"]:
        if _occ_col in available_cols and _occ_col not in join_cols:
            join_cols.append(_occ_col)
            break

    # Add value columns if available
    for _val_col in ["val_struct", "building_cost", "buildingcostusd", "replacement_cost"]:
        if _val_col in available_cols and _val_col not in join_cols:
            join_cols.append(_val_col)
            break

    for _val_col in ["val_cont", "content_cost", "contentcostusd", "contents_cost"]:
        if _val_col in available_cols and _val_col not in join_cols:
            join_cols.append(_val_col)
            break

    # Join losses to buildings for spatial analysis
    losses_join_df = losses_df.merge(
        buildings_df[join_cols], 
        left_on="id", 
        right_on=id_col,
        how="left"
    )
    return (
        aal_df,
        db_path,
        has_aal,
        losses_df,
        losses_join_df,
        validation_df,
    )


@app.cell
def _(
    aal_df,
    analysis_results,
    has_aal,
    losses_df,
    mo,
    validation_df,
):
    """Summary Statistics Cards"""

    # Calculate key metrics
    total_processed = analysis_results["buildings_loaded"]
    total_loss_mean = losses_df["loss_mean"].sum()
    buildings_with_loss = (losses_df.groupby("id")["loss_mean"].sum() > 0).sum()
    loss_pct = (buildings_with_loss / total_processed * 100)

    # Count validation issues
    error_count = (validation_df["severity"] == "ERROR").sum()
    warning_count = (validation_df["severity"] == "WARNING").sum()

    # AAL total if available
    aal_total = aal_df["aal_mean"].sum() if has_aal and aal_df is not None and len(aal_df) > 0 else None

    # Create stat cards
    cards = [
        mo.stat(
            label="Total Buildings",
            value=f"{total_processed:,}",
            caption="processed"
        ),
        mo.stat(
            label="Total Loss (Mean)",
            value=f"${total_loss_mean:,.0f}",
            caption="across all return periods",
            bordered=True
        ),
        mo.stat(
            label="Buildings with Loss",
            value=f"{buildings_with_loss:,}",
            caption=f"{loss_pct:.1f}% of total"
        )
    ]

    if aal_total is not None:
        cards.append(
            mo.stat(
                label="Annual Average Loss",
                value=f"${aal_total:,.0f}",
                caption="expected yearly loss",
                bordered=True
            )
        )

    if error_count > 0 or warning_count > 0:
        cards.append(
            mo.stat(
                label="Validation Issues",
                value=f"⚠️ {error_count + warning_count}",
                caption=f"{error_count} errors, {warning_count} warnings"
            )
        )

    mo.hstack(cards, justify="space-around")
    return


@app.cell
def _(losses_join_df, mo):
    """Results Section Header"""

    # This cell depends on losses_join_df to only show after analysis completes
    _ = losses_join_df  # ensure dependency
    mo.md("## 📊 Analysis Results")
    return


@app.cell
def _(
    LinearSegmentedColormap,
    Map,
    ScatterplotLayer,
    alt,
    apply_continuous_cmap,
    gpd,
    losses_join_df,
    mo,
    validation_df,
):
    """Results Visualization Tabs"""

    # Use all losses (no filtering)
    filtered_losses = losses_join_df.copy()

    # Tab 1: Loss Distribution Histogram
    hist_fig = alt.Chart(filtered_losses).mark_bar().encode(
        x=alt.X("loss_mean:Q", bin=alt.Bin(maxbins=50), title="Mean Loss ($)"),
        y=alt.Y("count()", title="Number of Buildings"),
        color=alt.value("#4682B4")
    ).properties(
        title="Distribution of Mean Losses",
        width=600,
        height=400
    )

    # Tab 2: Loss by Occupancy Type Box Plot
    # Find occupancy column if it exists
    occ_col = None
    for candidate in ["occtype", "occupancy_type", "occupancy", "occ_type", "building_type"]:
        if candidate in filtered_losses.columns:
            occ_col = candidate
            break

    if occ_col:
        box_fig = alt.Chart(filtered_losses).mark_boxplot().encode(
            x=alt.X(f"{occ_col}:N", title="Occupancy Type"),
            y=alt.Y("loss_mean:Q", title="Mean Loss ($)"),
            color=alt.Color(f"{occ_col}:N", legend=None)
        ).properties(
            title="Loss Distribution by Occupancy Type",
            width=600,
            height=400
        )
    else:
        box_fig = mo.md("*Occupancy type data not available*")

    # Tab 3: Validation Log Table
    validation_styled = validation_df.copy()

    # Color code by severity
    def severity_color(severity):
        if severity == "ERROR":
            return "🔴"
        elif severity == "WARNING":
            return "🟡"
        else:
            return "🔵"

    validation_styled["severity_icon"] = validation_styled["severity"].apply(severity_color)

    # Group by message and severity to get counts
    validation_summary = validation_df.groupby(["severity", "message"]).size().reset_index(name="count")
    validation_summary["severity_icon"] = validation_summary["severity"].apply(severity_color)
    validation_display = validation_summary[["severity_icon", "severity", "message", "count"]]

    # Tab 4: Interactive Map
    # Find coordinate columns
    _x_col = next((c for c in ["x", "longitude", "lon"] if c in filtered_losses.columns), None)
    _y_col = next((c for c in ["y", "latitude", "lat"] if c in filtered_losses.columns), None)

    if _x_col and _y_col and len(filtered_losses) > 0:
        map_gdf = gpd.GeoDataFrame(
            filtered_losses,
            geometry=gpd.points_from_xy(filtered_losses[_x_col], filtered_losses[_y_col]),
            crs="EPSG:4326"
        )

        # Normalize losses for color mapping
        loss_normalized = map_gdf['loss_mean'] / map_gdf['loss_mean'].max()

        # Create custom colormap
        colors_list = ['blue', 'green', 'yellow', 'red']
        custom_cmap = LinearSegmentedColormap.from_list('custom_cmap', colors_list)

        # Apply power transform
        stretched_values = loss_normalized ** 0.25
        colors = apply_continuous_cmap(stretched_values.to_numpy(), cmap=custom_cmap)

        layer = ScatterplotLayer.from_geopandas(
            map_gdf,
            get_fill_color=colors,
            get_radius=15,
            pickable=True,
        )

        loss_map = Map(layer)
        map_count = len(map_gdf)
    elif not _x_col or not _y_col:
        loss_map = mo.md("*Coordinate data (x/y or lon/lat) not available in buildings data*")
        map_count = 0
    else:
        loss_map = mo.md("*No buildings to display*")
        map_count = 0

    # Create tabs
    results_tabs = mo.ui.tabs({
        "📊 Summary": mo.vstack([
            mo.md(f"**{len(filtered_losses):,} buildings** analyzed"),
            mo.ui.altair_chart(hist_fig)
        ]),
        "📈 By Occupancy": mo.ui.altair_chart(box_fig) if occ_col else box_fig,
        "⚠️ Validation": mo.vstack([
            mo.md(f"**{len(validation_df)} validation messages**"),
            mo.ui.table(validation_display, selection=None)
        ]),
        "🗺️ Map": mo.vstack([
            mo.md(f"**{map_count:,} buildings** displayed on map"),
            loss_map
        ])
    })

    results_tabs
    return


@app.cell
def _(has_aal, mo):
    """Export UI Configuration"""

    # Get available tables from database (this cell only runs after analysis completes)
    available_tables = ["losses", "buildings", "validation_log"]
    if has_aal:
        available_tables.append("aal_losses")

    # Table selection dropdown
    export_table = mo.ui.dropdown(
        options=available_tables,
        value="losses",
        label="Table to Export"
    )

    # Export format selection
    export_format = mo.ui.dropdown(
        options=["csv", "parquet", "geoparquet", "geopackage"],
        value="csv",
        label="Export Format"
    )

    # Wide format option
    export_wide_checkbox = mo.ui.checkbox(
        value=False,
        label="Export summary format (one row per building)"
    )

    # Include geometry option (for spatial formats)
    include_geometry = mo.ui.checkbox(
        value=True,
        label="Include Geometry (for geoparquet/geopackage)"
    )

    # Export button
    export_button = mo.ui.run_button(label="📥 Export Data", kind="success")

    # Display the export UI (this cell only runs after analysis completes)
    mo.vstack([
        mo.md("## 💾 Export Results"),
        mo.md("Configure your export settings:"),
        export_table,
        export_format,
        export_wide_checkbox,
        include_geometry,
        mo.md("---"),
        export_button
    ])
    return (
        export_button,
        export_format,
        export_table,
        export_wide_checkbox,
        include_geometry,
    )


@app.cell
def _(
    db_path,
    duckdb,
    export_button,
    export_format,
    export_table,
    export_wide_checkbox,
    gpd,
    include_geometry,
    mo,
    os,
    output_directory,
    time,
):
    """Execute Export"""

    # Wait for export button click
    mo.stop(not export_button.value, "")

    # Extract output directory path from file browser
    if output_directory and len(output_directory) > 0:
        output_dir = str(output_directory[0].path)
    else:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    # Perform export
    try:
        # Handle wide format export using existing utility
        if export_wide_checkbox.value and export_table.value == "losses":
            # Import the export_wide utility (it manages its own connection)
            import sys
            examples_dir = os.path.dirname(os.path.abspath(__file__))
            if examples_dir not in sys.path:
                sys.path.insert(0, examples_dir)
            from utils import export_wide as export_wide_util

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            os.makedirs(output_dir, exist_ok=True)

            # Determine extension based on format
            if export_format.value == "geoparquet" and include_geometry.value:
                ext = "geoparquet"
            elif export_format.value == "geopackage" and include_geometry.value:
                ext = "gpkg"
            elif export_format.value in ["parquet", "geoparquet"]:
                ext = "parquet"
            else:
                ext = "csv"

            filename = f"losses_export_wide_{timestamp}.{ext}"
            filepath = os.path.join(output_dir, filename)

            # Call export_wide utility
            result_gdf, export_path = export_wide_util(
                db_path=db_path,
                output_path=filepath,
                output_format=ext,
                include_geometry=include_geometry.value
            )

            file_size = os.path.getsize(export_path)
            msg = f"✅ **Exported wide format**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Buildings**: {len(result_gdf):,}\n- **Location**: `{output_dir}`"
            if include_geometry.value and ext in ["geoparquet", "gpkg"]:
                msg += "\n- **CRS**: WGS84 (EPSG:4326) assumed for coordinates"
            _export_status = mo.callout(mo.md(msg), kind="success")

        else:
            # Standard table export (long format)
            # Open a fresh connection for this export
            export_conn = duckdb.connect(db_path, read_only=True)
            
            try:
                table_name = export_table.value

                # Handle geometry column for buildings table
                if table_name == "buildings":
                    export_data = export_conn.execute(f"SELECT * EXCLUDE (geometry) FROM {table_name}").fetch_df()
                else:
                    export_data = export_conn.execute(f"SELECT * FROM {table_name}").fetch_df()
                
                # For geoparquet/geopackage export, join with buildings table to get coordinates if needed
                if export_format.value in ["geoparquet", "geopackage"] and include_geometry.value:
                    has_coords = any(col in export_data.columns for col in ["x", "y", "longitude", "latitude"])
                    if not has_coords and "id" in export_data.columns and table_name != "buildings":
                        # Join with buildings table to get coordinates
                        coords_df = export_conn.execute(
                            "SELECT id, x, y FROM buildings WHERE x IS NOT NULL AND y IS NOT NULL"
                        ).fetch_df()
                        export_data = export_data.merge(coords_df, on="id", how="left")
            finally:
                export_conn.close()

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            os.makedirs(output_dir, exist_ok=True)

            # Create filename (use .gpkg extension for geopackage)
            file_ext = "gpkg" if export_format.value == "geopackage" else export_format.value
            filename = f"{table_name}_export_{timestamp}.{file_ext}"
            filepath = os.path.join(output_dir, filename)

            # Export based on format
            if export_format.value == "csv":
                export_data.to_csv(filepath, index=False)
                file_size = os.path.getsize(filepath)
                _export_status = mo.callout(
                    mo.md(f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                    kind="success"
                )

            elif export_format.value == "parquet":
                export_data.to_parquet(filepath, index=False)
                file_size = os.path.getsize(filepath)
                _export_status = mo.callout(
                    mo.md(f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                    kind="success"
                )

            elif export_format.value == "geoparquet":
                # Find coordinate columns (may have been joined from buildings table)
                _x_col = next((col for col in ["x", "longitude", "lon"] if col in export_data.columns), None)
                _y_col = next((col for col in ["y", "latitude", "lat"] if col in export_data.columns), None)

                if include_geometry.value and _x_col and _y_col:
                    # Filter out rows without coordinates
                    valid_coords = export_data[_x_col].notna() & export_data[_y_col].notna()
                    if valid_coords.sum() > 0:
                        export_gdf = gpd.GeoDataFrame(
                            export_data[valid_coords],
                            geometry=gpd.points_from_xy(
                                export_data.loc[valid_coords, _x_col],
                                export_data.loc[valid_coords, _y_col]
                            ),
                            crs="EPSG:4326"
                        )
                        export_gdf.to_parquet(filepath)
                        file_size = os.path.getsize(filepath)
                        rows_with_coords = valid_coords.sum()
                        rows_without = len(export_data) - rows_with_coords
                        msg = f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {rows_with_coords:,}\n- **Location**: `{output_dir}`\n- **CRS**: WGS84 (EPSG:4326) assumed for coordinates"
                        if rows_without > 0:
                            msg += f"\n- **Note**: {rows_without:,} rows excluded (missing coordinates)"
                        _export_status = mo.callout(mo.md(msg), kind="success")
                    else:
                        export_data.to_parquet(filepath, index=False)
                        file_size = os.path.getsize(filepath)
                        _export_status = mo.callout(
                            mo.md(f"⚠️ **Exported {table_name}** (no valid coordinates found): `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                            kind="warning"
                        )
                else:
                    export_data.to_parquet(filepath, index=False)
                    file_size = os.path.getsize(filepath)
                    _export_status = mo.callout(
                        mo.md(f"⚠️ **Exported {table_name}** (no coordinates available): `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                        kind="warning"
                    )

            elif export_format.value == "geopackage":
                # Find coordinate columns (may have been joined from buildings table)
                _x_col = next((col for col in ["x", "longitude", "lon"] if col in export_data.columns), None)
                _y_col = next((col for col in ["y", "latitude", "lat"] if col in export_data.columns), None)

                if include_geometry.value and _x_col and _y_col:
                    # Filter out rows without coordinates
                    valid_coords = export_data[_x_col].notna() & export_data[_y_col].notna()
                    if valid_coords.sum() > 0:
                        export_gdf = gpd.GeoDataFrame(
                            export_data[valid_coords],
                            geometry=gpd.points_from_xy(
                                export_data.loc[valid_coords, _x_col],
                                export_data.loc[valid_coords, _y_col]
                            ),
                            crs="EPSG:4326"
                        )
                        export_gdf.to_file(filepath, driver='GPKG')
                        file_size = os.path.getsize(filepath)
                        rows_with_coords = valid_coords.sum()
                        rows_without = len(export_data) - rows_with_coords
                        msg = f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {rows_with_coords:,}\n- **Location**: `{output_dir}`\n- **CRS**: WGS84 (EPSG:4326) assumed for coordinates"
                        if rows_without > 0:
                            msg += f"\n- **Note**: {rows_without:,} rows excluded (missing coordinates)"
                        _export_status = mo.callout(mo.md(msg), kind="success")
                    else:
                        _export_status = mo.callout(
                            mo.md(f"❌ **Export failed**: No valid coordinates found for geopackage export"),
                            kind="danger"
                        )
                else:
                    _export_status = mo.callout(
                        mo.md(f"❌ **Export failed**: Geopackage requires geometry. Enable 'Include Geometry' and ensure coordinates are available."),
                        kind="danger"
                    )

            else:
                _export_status = mo.callout(
                    mo.md(f"❌ **Unknown export format**: {export_format.value}"),
                    kind="danger"
                )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        _export_status = mo.callout(
            mo.md(f"❌ **Export failed**: {str(e)}\n\n```\n{error_details}\n```"),
            kind="danger"
        )

    _export_status
    return


@app.cell
def _(mo):
    """Footer"""
    mo.md(
        """
        ---

        **Inland Flood Analysis Tool** | FEMA FFRD | [Documentation](../docs/inland_methodology.md)
        """
    )
    return


if __name__ == "__main__":
    app.run()
