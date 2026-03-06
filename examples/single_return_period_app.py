import marimo

__generated_with = "0.20.2"
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
        mo, os, time, gpd, pd, np, duckdb, Path,
        NsiBuildings, MillimanBuildings, InlandFloodVulnerability, InlandFloodAnalysis,
        RasterCollection, SingleValueRaster,
        Map, ScatterplotLayer, apply_continuous_cmap,
        LinearSegmentedColormap, plt, alt
    )


@app.cell
def _(mo):
    """App Header"""
    mo.md(
        """
        # 🌊 Inland Consequences Solution
        
        Configure analysis parameters below, then click **Run Analysis** to calculate flood losses for your building inventory.
        
        💡 **Tip**: Default paths are pre-filled. Edit them to point to your data files.
        
        [Documentation](../docs/inland_methodology.md) | [GitHub](https://github.com/fema-ffrd/inland-consequences)
        """
    )
    return


@app.cell
def _(mo, os, Path):
    """Configuration - Basic Settings"""
    
    # Get default paths
    notebooks_dir = os.path.dirname(os.path.abspath(__file__))
    default_data_path = os.path.join(notebooks_dir, 'goldsmith_co_hazard_data')
    default_output_path = os.path.join(os.path.dirname(notebooks_dir), 'outputs')
    
    # Building dataset type selector
    building_type_selector = mo.ui.dropdown(
        options=["NSI", "Milliman"],
        value="NSI",
        label="🏢 Building Dataset Type"
    )
    
    # Building inventory file selector
    building_file_selector = mo.ui.file_browser(
        initial_path=default_data_path,
        filetypes=[".parquet", ".gpkg", ".geojson"],
        label="📁 Building Inventory File"
    )
    
    # Output directory (text input since it may not exist yet)
    output_dir_input = mo.ui.text(
        value=default_output_path,
        label="💾 Output Directory",
        placeholder="Path to output directory (will be created)",
        full_width=True
    )
    
    # Advanced options
    calculate_aal_checkbox = mo.ui.checkbox(
        value=False,
        label="Calculate Annual Average Loss (AAL) - requires 3+ return periods"
    )
    
    wildcard_fields_select = mo.ui.multiselect(
        options=["foundation_type", "num_stories", "construction_type"],
        value=[],
        label="Wildcard Fields (ignore in damage function matching)"
    )
    
    mo.vstack([
        mo.md("## ⚙️ Basic Configuration"),
        mo.md("Select your building inventory file and configure output settings."),
        building_type_selector,
        building_file_selector,
        output_dir_input,
        mo.md("### 🔧 Advanced Options"),
        calculate_aal_checkbox,
        wildcard_fields_select
    ])
    
    return (
        building_file_selector, building_type_selector, output_dir_input, calculate_aal_checkbox, 
        wildcard_fields_select, notebooks_dir, default_data_path, default_output_path
    )


@app.cell
def _(mo):
    """Number of Return Periods Selector"""
    num_return_periods = mo.ui.number(
        start=1, stop=30, value=3, step=1,
        label="Number of Return Periods",
        full_width=False
    )
    
    mo.vstack([
        mo.md("## 🌊 Return Period Configurations"),
        mo.md("**How many return periods do you want to analyze?**"),
        num_return_periods,
        mo.md("*Note: AAL calculation requires at least 3 return periods*")
    ])
    
    return num_return_periods,


@app.cell
def _(mo, num_return_periods, default_data_path):
    """Dynamic Return Period Configurations"""
    
    # Common return period values for flood modeling
    # Typically: 2, 5, 10, 25, 50, 100, 200, 500, 1000 years
    # Extended with reasonable increments if more are needed
    default_rps = [
        2, 5, 10, 25, 50, 100, 200, 500, 1000,  # Standard values
        20, 75, 150, 300, 750,  # Additional intermediates
        15, 30, 40, 60, 80, 120, 175, 250, 350, 400, 600, 700, 800, 900,  # Fill-ins
        1, 3, 7, 12, 35  # Rare extremes
    ]
    
    # Create a batch configuration for each return period
    _rp_configs = []
    for _i in range(num_return_periods.value):
        _default_rp = default_rps[_i] if _i < len(default_rps) else (_i + 1) * 10
        _config = mo.md(
            """
            **Return Period (years):** {return_period}
            
            **🌊 Depth Raster (required):** {depth_raster}
            
            **💨 Velocity Raster (optional):** {velocity_raster}
            
            **⏱️ Duration Raster (optional):** {duration_raster}
            
            **📊 Uncertainty Raster (optional):** {uncertainty_raster}
            """
        ).batch(
            return_period=mo.ui.number(
                start=1, stop=1000000, value=_default_rp, step=1,
                label="Return Period (years)", full_width=True
            ),
            depth_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Depth Raster"
            ),
            velocity_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Velocity Raster"
            ),
            duration_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Duration Raster"
            ),
            uncertainty_raster=mo.ui.file_browser(
                initial_path=default_data_path,
                filetypes=[".tif", ".tiff"],
                label="Uncertainty Raster"
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
    
    return rp_configs_list,

@app.cell
def _(mo):
    """Submit Button"""
    submit_config = mo.ui.run_button(label="▶️ Validate & Run Analysis")
    
    mo.vstack([
        mo.md("---"),
        mo.md("## 🚀 Ready to Run?"),
        mo.md("Click the button below to validate your configuration and start the analysis."),
        submit_config
    ])
    return submit_config,


@app.cell
def _(mo, submit_config, building_file_selector, building_type_selector, output_dir_input, 
       calculate_aal_checkbox, wildcard_fields_select, rp_configs_list, os):
    """Validate Configuration"""
    
    # Stop execution if form not submitted
    mo.stop(not submit_config.value, mo.md("👆 **Configure parameters above and click Submit**"))
    
    # Extract building file from file browser
    if len(building_file_selector.value) == 0:
        mo.stop(True, mo.callout(
            mo.md("❌ **No building file selected**. Please select a building inventory file."),
            kind="danger"
        ))
    building_file = building_file_selector.value[0].path
    
    # Validate building file exists
    if not os.path.isfile(building_file):
        mo.stop(True, mo.callout(
            mo.md(f"❌ **Building file not found**: `{building_file}`"),
            kind="danger"
        ))
    
    # Get building dataset type
    building_type = building_type_selector.value
    
    # Get output directory
    output_directory = output_dir_input.value
    
    # Get wildcard fields
    wildcard_fields = list(wildcard_fields_select.value)
    
    # Get AAL setting
    calculate_aal = calculate_aal_checkbox.value
    
    # Parse and validate return period configurations
    return_periods_list = []
    raster_config = {}
    
    # Process each return period configuration
    for _i, _rp_config in enumerate(rp_configs_list):
        _rp_data = _rp_config.value
        _rp = _rp_data["return_period"]
        
        # Validate depth raster (required)
        if len(_rp_data["depth_raster"]) == 0:
            mo.stop(True, mo.callout(
                mo.md(f"❌ **No depth raster selected for Return Period {_i + 1}**. Depth is required."),
                kind="danger"
            ))
        
        _depth = _rp_data["depth_raster"][0].path
        if not os.path.isfile(_depth):
            mo.stop(True, mo.callout(
                mo.md(f"❌ **Depth raster not found for {_rp}-year**: `{_depth}`"),
                kind="danger"
            ))
        
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
    
    # Validate AAL requirements
    if calculate_aal and len(return_periods_list) < 3:
        mo.stop(True, mo.callout(
            mo.md(f"❌ **AAL calculation requires at least 3 return periods**. You have {len(return_periods_list)}. Increase the number of return periods."),
            kind="warning"
        ))
    
    validation_message = f"✅ Configuration valid: {len(return_periods_list)} return period(s) - {return_periods_list}"
    mo.md(validation_message)
    return (
        return_periods_list, raster_config, validation_message,
        building_file, building_type, output_directory, calculate_aal, wildcard_fields
    )


@app.cell
def _(mo, calculate_aal):
    """Workflow Visualization"""
    
    # Create mermaid diagram showing analysis workflow
    aal_style = "fill:#90EE90" if calculate_aal else "fill:#E0E0E0"
    
    workflow_diagram = f"""
    ```mermaid
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
        style F {aal_style}
        style G fill:#DDA0DD
    ```
    """
    
    mo.accordion({
        "📊 Analysis Workflow": mo.md(workflow_diagram)
    })
    return workflow_diagram, aal_style



@app.cell
def _(mo, raster_config, return_periods_list, pd):
    """Raster Collection Preview"""
    
    # Create preview dataframe showing configured rasters
    preview_data = []
    for _rp in return_periods_list:
        _files = raster_config[_rp]
        preview_data.append({
            "Return Period": _rp,
            "Depth": "✅",
            "Velocity": "✅" if "velocity" in _files else "⬜",
            "Duration": "✅" if "duration" in _files else "⬜",
            "Uncertainty": "✅" if "uncertainty" in _files else "⬜"
        })
    
    preview_df = pd.DataFrame(preview_data)
    
    mo.vstack([
        mo.md("**📁 Configured Hazard Rasters**"),
        mo.ui.table(preview_df, selection=None)
    ])
    return preview_data, preview_df


@app.cell
def _(mo):
    """Execution Button"""
    run_button = mo.ui.run_button(label="▶️ Run Analysis", kind="success")
    run_button
    return run_button,


@app.cell
def _(mo, run_button, building_file, building_type, calculate_aal, wildcard_fields,
      raster_config, return_periods_list, 
      gpd, os, time, NsiBuildings, MillimanBuildings, InlandFloodVulnerability, 
      InlandFloodAnalysis, RasterCollection, SingleValueRaster):
    """Execute Analysis with Status Tracking"""
    
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
            wildcard_fields=wildcard_fields
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
    return (
        analysis, analysis_results, buildings, gdf, 
        flood_function, raster_collection, start_time, 
        step_start, total_time
    )


@app.cell
def _(mo, run_button, analysis_results, duckdb):
    """Load Results from Database"""
    
    mo.stop(not run_button.value, "")
    
    # Connect to results database
    db_path = analysis_results["db_path"]
    conn = duckdb.connect(db_path)
    
    # Load key tables
    losses_df = conn.execute("SELECT * FROM losses").fetch_df()
    buildings_df = conn.execute("SELECT * FROM buildings").fetch_df()
    validation_df = conn.execute("SELECT * FROM validation_log").fetch_df()
    
    # Check for AAL table
    tables = conn.execute("SHOW TABLES").fetch_df()
    has_aal = "aal_losses" in tables["name"].values
    
    if has_aal:
        aal_df = conn.execute("SELECT * FROM aal_losses").fetch_df()
    else:
        aal_df = None
    
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
        conn, db_path, losses_df, buildings_df, 
        validation_df, tables, has_aal, aal_df, 
        losses_join_df, join_cols, id_col
    )


@app.cell
def _(mo, run_button, losses_df, validation_df, aal_df, has_aal):
    """Summary Statistics Cards"""
    
    mo.stop(not run_button.value, "")
    
    # Calculate key metrics
    total_buildings = len(losses_df["id"].unique())
    total_loss_mean = losses_df["loss_mean"].sum()
    buildings_with_loss = (losses_df.groupby("id")["loss_mean"].sum() > 0).sum()
    zero_loss_pct = ((total_buildings - buildings_with_loss) / total_buildings * 100)
    
    # Count validation issues
    error_count = (validation_df["severity"] == "ERROR").sum()
    warning_count = (validation_df["severity"] == "WARNING").sum()
    
    # AAL total if available
    aal_total = aal_df["aal_mean"].sum() if has_aal and aal_df is not None and len(aal_df) > 0 else None
    
    # Create stat cards
    cards = [
        mo.stat(
            label="Total Buildings",
            value=f"{total_buildings:,}",
            caption="analyzed"
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
            caption=f"{100-zero_loss_pct:.1f}% of total"
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
    return (
        total_buildings, total_loss_mean, buildings_with_loss, 
        zero_loss_pct, error_count, warning_count, aal_total, cards
    )


@app.cell
def _(mo, run_button):
    """Results Section Header"""
    
    mo.stop(not run_button.value, "")
    
    mo.md("## 📊 Analysis Results")
    return


@app.cell
def _(mo, run_button, losses_join_df, gpd, pd, 
      apply_continuous_cmap, LinearSegmentedColormap, alt, validation_df,
      Map, ScatterplotLayer):
    """Results Visualization Tabs"""
    
    mo.stop(not run_button.value, "")
    
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
    return (
        filtered_losses, hist_fig, box_fig, validation_styled, validation_summary,
        validation_display, loss_map, results_tabs, severity_color,
        occ_col, map_count
    )


@app.cell
def _(mo, run_button, conn, has_aal):
    """Export UI Configuration"""
    
    # Always create the UI elements, but only display when analysis is done
    # Get available tables from database
    available_tables = ["losses", "buildings", "validation_log"]
    if run_button.value and has_aal:
        available_tables.append("aal_losses")
    
    # Table selection dropdown
    export_table = mo.ui.dropdown(
        options=available_tables if run_button.value else ["losses"],
        value="losses",
        label="Table to Export"
    )
    
    # Export format selection
    export_format = mo.ui.dropdown(
        options=["csv", "parquet", "geoparquet"],
        value="csv",
        label="Export Format"
    )
    
    # Wide format option
    export_wide_checkbox = mo.ui.checkbox(
        value=False,
        label="Export Wide Format (pivot by return period)"
    )
    
    # Include geometry option (for geoparquet)
    include_geometry = mo.ui.checkbox(
        value=True,
        label="Include Geometry (for geoparquet)"
    )
    
    # Export button
    export_button = mo.ui.run_button(label="📥 Export Data", kind="success")
    
    # Display the export UI after analysis runs
    _export_ui = mo.vstack([
        mo.md("## 💾 Export Results"),
        mo.md("Configure your export settings:"),
        export_table,
        export_format,
        export_wide_checkbox,
        include_geometry,
        mo.md("---"),
        export_button
    ]) if run_button.value else None
    
    if _export_ui is not None:
        _export_ui
    
    return export_table, export_format, export_wide_checkbox, include_geometry, export_button


@app.cell
def _(mo, run_button, export_button, export_table, export_format, 
      export_wide_checkbox, include_geometry, conn, db_path, output_directory, os, gpd, pd, time):
    """Execute Export"""
    
    # Check if analysis has been run
    if not run_button.value:
        _export_status = None
    # Check if export button has been clicked
    elif not export_button.value:
        _export_status = mo.callout(
            mo.md("👆 **Click the Export Data button above to export results**"),
            kind="info"
        )
    else:
        # Perform export
        try:
            # Handle wide format export using existing utility
            if export_wide_checkbox.value and export_table.value == "losses":
                # Import the export_wide utility
                import sys
                examples_dir = os.path.dirname(os.path.abspath(__file__))
                if examples_dir not in sys.path:
                    sys.path.insert(0, examples_dir)
                from utils import export_wide as export_wide_util
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_dir = output_directory
                os.makedirs(output_dir, exist_ok=True)
                
                # Determine extension based on format
                if export_format.value == "geoparquet" and include_geometry.value:
                    ext = "geoparquet"
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
                _export_status = mo.callout(
                    mo.md(f"✅ **Exported wide format**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Buildings**: {len(result_gdf):,}\n- **Location**: `{output_dir}`"),
                    kind="success"
                )
            
            else:
                # Standard table export (long format)
                table_name = export_table.value
                export_data = conn.execute(f"SELECT * FROM {table_name}").fetch_df()
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_dir = output_directory
                os.makedirs(output_dir, exist_ok=True)
                
                # Create filename
                filename = f"{table_name}_export_{timestamp}.{export_format.value}"
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
                    if include_geometry.value and any(col in export_data.columns for col in ["x", "y", "longitude", "latitude"]):
                        # Find coordinate columns
                        _x_col = next((col for col in ["x", "longitude", "lon"] if col in export_data.columns), None)
                        _y_col = next((col for col in ["y", "latitude", "lat"] if col in export_data.columns), None)
                        
                        if _x_col and _y_col:
                            export_gdf = gpd.GeoDataFrame(
                                export_data,
                                geometry=gpd.points_from_xy(export_data[_x_col], export_data[_y_col]),
                                crs="EPSG:4326"
                            )
                            export_gdf.to_parquet(filepath)
                            file_size = os.path.getsize(filepath)
                            _export_status = mo.callout(
                                mo.md(f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                                kind="success"
                            )
                        else:
                            export_data.to_parquet(filepath, index=False)
                            file_size = os.path.getsize(filepath)
                            _export_status = mo.callout(
                                mo.md(f"⚠️ **Exported {table_name}** (no coordinates found): `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                                kind="warning"
                            )
                    else:
                        export_data.to_parquet(filepath, index=False)
                        file_size = os.path.getsize(filepath)
                        _export_status = mo.callout(
                            mo.md(f"✅ **Exported {table_name}**: `{filename}`\n\n- **Size**: {file_size/1024:.1f} KB\n- **Rows**: {len(export_data):,}\n- **Location**: `{output_dir}`"),
                            kind="success"
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
    
    # Display the export status (only when there's something to show)
    if _export_status is not None:
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
