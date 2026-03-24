"""Flood Results Explorer — interactive Marimo notebook.

Visualises flood loss results from a completed InlandFloodAnalysis DuckDB run
using FloodResultsAggregator.  The notebook dynamically detects the appropriate
census geography levels to display:

* **Summary table** — single top-level unit (e.g. the one county with results)
  showing all return period losses and AAL min/mean/max.
* **Choropleth + top-10 table** — drill-down level that produces multiple result
  units (e.g. census tracts within that county).
* **Breakdown section** — reactive charts and table driven by a dropdown that
  selects the building attribute dimension (occupancy type, damage category, etc.)

Run with:
    uv run marimo edit examples/notebooks/flood_results_explorer.py

or as a read-only app:
    uv run marimo run examples/notebooks/flood_results_explorer.py
"""

import marimo

__generated_with = "0.20.3"
app = marimo.App(width="full", app_title="Flood Results Explorer")


@app.cell
def _imports():
    import io
    import sys
    from pathlib import Path

    import duckdb
    import geopandas as gpd
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import marimo as mo
    import numpy as np
    import pandas as pd
    import pygris
    from great_tables import GT, loc, style

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from inland_consequences.results_aggregation import FloodResultsAggregator

    return (
        FloodResultsAggregator,
        GT,
        Path,
        duckdb,
        gpd,
        io,
        mo,
        mpl,
        pd,
        plt,
        pygris,
    )


@app.cell
def _header(mo):
    mo.md(r"""
    # 🌊 Flood Results Explorer

    Aggregated inland flood loss results from a completed `InlandFloodAnalysis` run.
    The notebook auto-detects the appropriate census geography levels: a **summary
    table** at the coarsest level with results, and a **choropleth + top-10 table**
    at the finer level that yields multiple result units.
    """)
    return


@app.cell
def _db_picker(Path, mo):
    _root = Path(__file__).parent.parent
    _excluded_dirs = {"tests", "outputs"}

    _candidates = []
    for _p in sorted(_root.rglob("*.duckdb")):
        _rel_parts = set(_p.relative_to(_root).parts[:-1])
        if _rel_parts & _excluded_dirs:
            continue
        if _p.name.startswith("test_"):
            continue
        _candidates.append(_p)

    _db_options = {str(p.relative_to(_root)): p for p in _candidates}
    _db_default = next(iter(_db_options)) if _db_options else None

    GEO_LEVEL_ORDER = ["state", "county", "tract", "block_group", "block", "community", "huc"]
    _GEO_LABELS = {
        "state": "State",
        "county": "County",
        "tract": "Tract",
        "block_group": "Block Group",
        "block": "Block",
        "community": "Community",
        "huc": "HUC (Watershed)",
    }

    db_file_dropdown = mo.ui.dropdown(
        options=_db_options,
        value=_db_default,
        label="DuckDB file",
    )
    geo_level_multiselect = mo.ui.multiselect(
        options={_GEO_LABELS[lvl]: lvl for lvl in GEO_LEVEL_ORDER},
        value=["State", "County", "Tract"],
        label="Geography hierarchy (coarse → fine)",
    )
    view_button = mo.ui.run_button(label="▶ View Results")

    mo.vstack([
        mo.md("### Configure Analysis"),
        mo.hstack([db_file_dropdown, geo_level_multiselect], gap=2),
        view_button,
    ])
    return (
        GEO_LEVEL_ORDER,
        db_file_dropdown,
        geo_level_multiselect,
        view_button,
    )


@app.cell
def _config(
    GEO_LEVEL_ORDER,
    db_file_dropdown,
    geo_level_multiselect,
    mo,
    view_button,
):
    mo.stop(
        not view_button.value,
        mo.callout(
            mo.md("Select a DuckDB file and geography levels, then click **▶ View Results**."),
            kind="info",
        ),
    )
    DB_PATH = db_file_dropdown.value
    HIERARCHY = [lvl for lvl in GEO_LEVEL_ORDER if lvl in set(geo_level_multiselect.value)]
    return DB_PATH, HIERARCHY


@app.cell
def _load_data(DB_PATH, FloodResultsAggregator, HIERARCHY, duckdb, mo):
    _HIERARCHY = HIERARCHY
    BREAKDOWN_DIMS = {
        "Occupancy Type": "occupancy_type",
        "Damage Category": "st_damcat",
        "Building Type": "general_building_type",
        "Foundation Type": "foundation_type",
        "Flood Peril Type": "flood_peril_type",
    }

    _conn = duckdb.connect(str(DB_PATH), read_only=True)
    _agg = FloodResultsAggregator(conn=_conn)
    return_periods = _agg.get_return_periods()

    # Run aggregations at each level and count units with actual results
    _level_dfs: dict = {}
    _level_counts: dict = {}
    for _lvl in _HIERARCHY:
        _df = _agg.aggregate(geography=_lvl)
        _level_dfs[_lvl] = _df
        _level_counts[_lvl] = int((_df["aal_mean"].notna() & (_df["aal_mean"] > 0)).sum())

    # summary_level = finest level with exactly 1 result unit
    # comparison_level = next level down that has >1 result units
    summary_level = None
    comparison_level = None
    for _i, _lvl in enumerate(_HIERARCHY):
        _n = _level_counts[_lvl]
        if _n > 1:
            comparison_level = _lvl
            summary_level = _HIERARCHY[_i - 1] if _i > 0 else None
            break

    # Fallback: if no level has >1 results, use deepest available level as comparison
    if comparison_level is None:
        for _i in range(len(_HIERARCHY) - 1, -1, -1):
            if _level_counts[_HIERARCHY[_i]] > 0:
                comparison_level = _HIERARCHY[min(_i + 1, len(_HIERARCHY) - 1)]
                summary_level = _HIERARCHY[_i]
                break

    # DataFrames for each role
    summary_df = _level_dfs.get(summary_level) if summary_level else None
    comparison_df = _level_dfs[comparison_level]

    # Preload all 5 breakdown aggregations at the comparison level
    breakdowns_data: dict = {}
    for _dim_col in BREAKDOWN_DIMS.values():
        breakdowns_data[_dim_col] = _agg.aggregate(
            geography=comparison_level, breakdown=[_dim_col]
        )

    _n_summary = (
        int((summary_df["aal_mean"].notna() & (summary_df["aal_mean"] > 0)).sum())
        if summary_df is not None else 0
    )
    _n_comparison = int(
        (comparison_df["aal_mean"].notna() & (comparison_df["aal_mean"] > 0)).sum()
    )

    mo.md(
        f"**Database:** `{DB_PATH.name}` &nbsp;|&nbsp; "
        f"**Summary level:** `{summary_level}` ({_n_summary} unit(s) with results) &nbsp;|&nbsp; "
        f"**Comparison level:** `{comparison_level}` ({_n_comparison} units with results) &nbsp;|&nbsp; "
        f"**Return periods:** {return_periods}"
    )
    return (
        BREAKDOWN_DIMS,
        breakdowns_data,
        comparison_df,
        comparison_level,
        return_periods,
        summary_df,
        summary_level,
    )


@app.cell
def _ui_controls(BREAKDOWN_DIMS, mo, return_periods):
    _metric_options = {
        "AAL (mean $)": "aal_mean",
        "AAL Min ($)": "aal_min",
        "AAL Max ($)": "aal_max",
        "AAL Ratio ($/M exposure)": "aal_ratio",
        **{f"RP-{rp} Loss ($)": f"loss_rp{rp}" for rp in return_periods},
        **{f"RP-{rp} Loss Ratio ($/M)": f"loss_ratio_rp{rp}" for rp in return_periods},
    }
    metric_dropdown = mo.ui.dropdown(
        options=_metric_options,
        value="AAL (mean $)",
        label="Map metric",
    )
    _breakdown_options = {"Total (no breakdown)": None, **BREAKDOWN_DIMS}
    breakdown_dropdown = mo.ui.dropdown(
        options=_breakdown_options,
        value="Total (no breakdown)",
        label="Breakdown by",
    )
    mo.hstack([metric_dropdown, breakdown_dropdown], gap=2)
    return breakdown_dropdown, metric_dropdown


@app.cell
def _section_geographic(comparison_level, mo, summary_level):
    _sum_lbl = summary_level.replace("_", " ").title() if summary_level else "—"
    _cmp_lbl = comparison_level.replace("_", " ").title()
    mo.md(f"""
    ## 📍 Geographic Summary

    **Summary table** shows the {_sum_lbl}-level unit(s) with results.
    **Choropleth and top-10 table** are rendered at the {_cmp_lbl} level.
    """)
    return


@app.cell
def _summary_table(GT, mo, pd, return_periods, summary_df, summary_level):
    _output = None
    if summary_df is None or not (
        summary_df["aal_mean"].notna() & (summary_df["aal_mean"] > 0)
    ).any():
        _output = mo.md("_No summary-level results available._")
    else:
        _geo_col = {
            "state": "state_fips",
            "county": "county_fips",
            "tract": "tract_fips",
            "block_group": "block_group_fips",
            "block": "block_fips",
        }[summary_level]

        _cols = (
            [_geo_col, "building_count", "total_building_exposure"]
            + [f"loss_rp{rp}" for rp in return_periods]
            + ["aal_min", "aal_mean", "aal_max", "aal_ratio"]
        )
        _display = summary_df[[c for c in _cols if c in summary_df.columns]].copy()
        _display = _display[
            _display["aal_mean"].notna() & (_display["aal_mean"] > 0)
        ].reset_index(drop=True)

        def _fmt_dollars(v):
            if pd.isna(v):
                return "—"
            if abs(v) >= 1e9:
                return f"${v/1e9:.2f}B"
            if abs(v) >= 1e6:
                return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        def _fmt_ratio(v):
            return "—" if pd.isna(v) else f"${v:,.0f}/M"

        _display_fmt = _display.copy()
        _display_fmt["building_count"] = _display_fmt["building_count"].apply(
            lambda v: "—" if pd.isna(v) else f"{int(v):,}"
        )
        _display_fmt["total_building_exposure"] = _display_fmt["total_building_exposure"].apply(_fmt_dollars)
        for _rp in return_periods:
            _col = f"loss_rp{_rp}"
            if _col in _display_fmt.columns:
                _display_fmt[_col] = _display_fmt[_col].apply(_fmt_dollars)
        for _c in ["aal_min", "aal_mean", "aal_max"]:
            if _c in _display_fmt.columns:
                _display_fmt[_c] = _display_fmt[_c].apply(_fmt_dollars)
        if "aal_ratio" in _display_fmt.columns:
            _display_fmt["aal_ratio"] = _display_fmt["aal_ratio"].apply(_fmt_ratio)

        _rp_cols = [f"loss_rp{rp}" for rp in return_periods if f"loss_rp{rp}" in _display_fmt.columns]
        _aal_cols = [c for c in ["aal_min", "aal_mean", "aal_max"] if c in _display_fmt.columns]
        _lbl = summary_level.replace("_", " ").title()

        _col_labels = {
            _geo_col: f"{_lbl} FIPS",
            "building_count": "Buildings",
            "total_building_exposure": "Exposure",
            **{f"loss_rp{rp}": f"RP-{rp}" for rp in return_periods},
            "aal_min": "AAL Min",
            "aal_mean": "AAL Mean",
            "aal_max": "AAL Max",
            "aal_ratio": "AAL Ratio",
        }

        _output = (
            GT(_display_fmt)
            .tab_header(
                title=f"{_lbl}-Level Flood Loss Summary",
                subtitle=f"{len(_display)} unit(s) with results",
            )
            .cols_label(**{k: v for k, v in _col_labels.items() if k in _display_fmt.columns})
            .tab_spanner(label="Return Period Losses", columns=_rp_cols)
            .tab_spanner(label="Annualized Loss (Uncertainty Range)", columns=_aal_cols)
            .tab_source_note("AAL = Average Annual Loss.  Ratio = USD per $1M exposure.")
        )
    _output
    return


@app.cell
def _comparison_geometries(
    comparison_df,
    comparison_level,
    gpd,
    pygris,
    summary_df,
    summary_level,
):
    _GEO_COL = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
    }
    _geo_col = _GEO_COL[comparison_level]

    # Derive state FIPS from first available result row
    _state_fips = comparison_df[_geo_col].str[:2].iloc[0]

    if comparison_level == "state":
        _raw = pygris.states(cb=True, resolution="500k", cache=True)
    elif comparison_level == "county":
        _raw = pygris.counties(state=_state_fips, cb=True, resolution="500k", cache=True)
    elif comparison_level == "tract":
        # Need county code(s) — derive from summary_df if available, else all counties
        if summary_df is not None and summary_level == "county":
            _summary_geo_col = _GEO_COL["county"]
            _county_codes = (
                summary_df[summary_df["aal_mean"].notna() & (summary_df["aal_mean"] > 0)][_summary_geo_col]
                .str[2:5]
                .unique()
                .tolist()
            )
        else:
            # Fall back: use county codes from comparison_df itself
            _county_codes = comparison_df[_geo_col].str[2:5].unique().tolist()

        _gdfs = [
            pygris.tracts(state=_state_fips, county=_c, cb=True, cache=True)
            for _c in _county_codes
        ]
        _raw = gpd.pd.concat(_gdfs, ignore_index=True)
    else:
        _raw = pygris.counties(state=_state_fips, cb=True, resolution="500k", cache=True)

    comparison_gdf = _raw.to_crs("EPSG:4326").merge(
        comparison_df,
        left_on="GEOID",
        right_on=_geo_col,
        how="left",
    )
    return (comparison_gdf,)


@app.cell
def _choropleth(
    comparison_gdf,
    comparison_level,
    metric_dropdown,
    mo,
    mpl,
    plt,
    return_periods,
):
    _metric_col = metric_dropdown.value

    # Build label map
    _label_map = {
        "aal_mean": "AAL (mean $)",
        "aal_min": "AAL Min ($)",
        "aal_max": "AAL Max ($)",
        "aal_ratio": "AAL Ratio ($/M exposure)",
        **{f"loss_rp{rp}": f"RP-{rp} Loss ($)" for rp in return_periods},
        **{f"loss_ratio_rp{rp}": f"RP-{rp} Loss Ratio ($/M)" for rp in return_periods},
    }
    _metric_label = _label_map.get(_metric_col, _metric_col)
    _cmp_lbl = comparison_level.replace("_", " ").title()

    _fig, _ax = plt.subplots(1, 1, figsize=(14, 8))
    _ax.set_facecolor("#e8f4f8")
    _fig.patch.set_facecolor("#f7fbff")

    _no_data = comparison_gdf[comparison_gdf[_metric_col].isna()]
    _has_data = comparison_gdf[comparison_gdf[_metric_col].notna()]

    _no_data.plot(ax=_ax, color="#d4d4d4", edgecolor="white", linewidth=0.3)

    if not _has_data.empty:
        _vmin = _has_data[_metric_col].min()
        _vmax = _has_data[_metric_col].max()
        _has_data.plot(
            ax=_ax,
            column=_metric_col,
            cmap="YlOrRd",
            edgecolor="white",
            linewidth=0.4,
            vmin=_vmin,
            vmax=_vmax,
        )
        _sm = mpl.cm.ScalarMappable(
            cmap="YlOrRd",
            norm=mpl.colors.Normalize(vmin=_vmin, vmax=_vmax),
        )
        _sm.set_array([])
        _cbar = _fig.colorbar(_sm, ax=_ax, fraction=0.025, pad=0.02)
        _cbar.set_label(_metric_label, fontsize=10)

        def _fmt_cbar(v, pos):
            if "ratio" in _metric_col.lower():
                return f"${v:,.0f}/M"
            if abs(v) >= 1e9:
                return f"${v/1e9:.1f}B"
            if abs(v) >= 1e6:
                return f"${v/1e6:.1f}M"
            if abs(v) >= 1e3:
                return f"${v/1e3:.1f}k"
            return f"${v:,.0f}"

        _cbar.ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(_fmt_cbar))

        def _fmt_val(v):
            if "ratio" in _metric_col.lower():
                return f"${v:,.0f}/M"
            return f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v:,.0f}"

        # Only annotate for county/state level (too many labels at tract)
        if comparison_level in ("county", "state"):
            for _, _row in _has_data.iterrows():
                _cx = _row.geometry.centroid.x
                _cy = _row.geometry.centroid.y
                _name = _row.get("NAME", "")
                _ax.annotate(
                    f"{_name}\n{_fmt_val(_row[_metric_col])}",
                    xy=(_cx, _cy),
                    ha="center", va="center",
                    fontsize=7.5, fontweight="bold", color="black",
                )

    if comparison_level in ("county", "state"):
        for _, _row in _no_data.iterrows():
            _cx = _row.geometry.centroid.x
            _cy = _row.geometry.centroid.y
            _ax.annotate(
                _row.get("NAME", ""), xy=(_cx, _cy),
                ha="center", va="center", fontsize=5.5, color="#666666",
            )

    _ax.set_title(
        f"{_cmp_lbl}-Level Flood Loss — {_metric_label}",
        fontsize=13, fontweight="bold", pad=10,
    )
    _ax.axis("off")
    _fig.tight_layout()
    mo.mpl.interactive(_fig)
    return


@app.cell
def _top10_table(GT, comparison_df, comparison_level, mo, pd, return_periods):
    _geo_col = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
    }[comparison_level]

    _results = (
        comparison_df[comparison_df["aal_mean"].notna() & (comparison_df["aal_mean"] > 0)]
        .sort_values("aal_mean", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    _output = None
    if _results.empty:
        _output = mo.md("_No comparison-level results available._")
    else:
        # Pick a representative set of RPs (max 4) to keep the table readable
        _show_rps = return_periods[:4] if len(return_periods) > 4 else return_periods
        _cols = (
            [_geo_col, "building_count", "total_building_exposure"]
            + [f"loss_rp{rp}" for rp in _show_rps]
            + ["aal_min", "aal_mean", "aal_max", "aal_ratio"]
        )
        _display = _results[[c for c in _cols if c in _results.columns]].copy()

        def _fmt_dollars(v):
            if pd.isna(v):
                return "—"
            if abs(v) >= 1e9:
                return f"${v/1e9:.2f}B"
            if abs(v) >= 1e6:
                return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        _display_fmt = _display.copy()
        _display_fmt["building_count"] = _display_fmt["building_count"].apply(
            lambda v: f"{int(v):,}" if not pd.isna(v) else "—"
        )
        _display_fmt["total_building_exposure"] = _display_fmt["total_building_exposure"].apply(_fmt_dollars)
        for _rp in _show_rps:
            _c = f"loss_rp{_rp}"
            if _c in _display_fmt.columns:
                _display_fmt[_c] = _display_fmt[_c].apply(_fmt_dollars)
        for _c in ["aal_min", "aal_mean", "aal_max"]:
            if _c in _display_fmt.columns:
                _display_fmt[_c] = _display_fmt[_c].apply(_fmt_dollars)
        if "aal_ratio" in _display_fmt.columns:
            _display_fmt["aal_ratio"] = _display_fmt["aal_ratio"].apply(
                lambda v: "—" if pd.isna(v) else f"${v:,.0f}/M"
            )

        _lbl = comparison_level.replace("_", " ").title()
        _rp_cols = [f"loss_rp{rp}" for rp in _show_rps if f"loss_rp{rp}" in _display_fmt.columns]
        _aal_cols = [c for c in ["aal_min", "aal_mean", "aal_max"] if c in _display_fmt.columns]

        _col_labels = {
            _geo_col: f"{_lbl} FIPS",
            "building_count": "Buildings",
            "total_building_exposure": "Exposure",
            **{f"loss_rp{rp}": f"RP-{rp}" for rp in _show_rps},
            "aal_min": "AAL Min",
            "aal_mean": "AAL Mean",
            "aal_max": "AAL Max",
            "aal_ratio": "AAL Ratio",
        }

        _output = (
            GT(_display_fmt)
            .tab_header(
                title=f"Top 10 {_lbl}s by Mean AAL",
                subtitle="Ranked by Average Annual Loss (mean)",
            )
            .cols_label(**{k: v for k, v in _col_labels.items() if k in _display_fmt.columns})
            .tab_spanner(label=f"RP Losses (first {len(_show_rps)})", columns=_rp_cols)
            .tab_spanner(label="AAL Uncertainty Range", columns=_aal_cols)
            .tab_source_note("AAL = Average Annual Loss.  Ratio = USD per $1M exposure.")
        )
    _output
    return


@app.cell
def _geo_summary_controls(comparison_level, mo):
    _ALL_GEO_LEVELS = ["state", "county", "tract", "block_group", "block", "community", "huc"]
    _GEO_LABELS = {
        "state": "State",
        "county": "County",
        "tract": "Tract",
        "block_group": "Block Group",
        "block": "Block",
        "community": "Community",
        "huc": "HUC (Watershed)",
    }
    geo_summary_dropdown = mo.ui.dropdown(
        options={_GEO_LABELS[lvl]: lvl for lvl in _ALL_GEO_LEVELS},
        value=_GEO_LABELS.get(comparison_level, "County"),
        label="Summarize by geography",
    )
    geo_summary_dropdown
    return (geo_summary_dropdown,)


@app.cell
def _geo_summary_gdf(
    DB_PATH,
    FloodResultsAggregator,
    duckdb,
    geo_summary_dropdown,
    gpd,
    mo,
    pd,
    pygris,
):
    _selected_level = geo_summary_dropdown.value
    _CENSUS_GEO_COL = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
    }

    _conn = duckdb.connect(str(DB_PATH), read_only=True)
    _agg_obj = FloodResultsAggregator(conn=_conn)
    _agg_df = _agg_obj.aggregate(geography=_selected_level)

    _status = None
    if _selected_level not in _CENSUS_GEO_COL:
        geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
        _status = mo.callout(
            mo.md(f"No census geometry available for **{_selected_level}** — showing tabular data only."),
            kind="warn",
        )
    else:
        _geo_col = _CENSUS_GEO_COL[_selected_level]
        _valid = _agg_df[_agg_df[_geo_col].notna()]
        if _valid.empty:
            geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
            _status = mo.callout(mo.md("No geography IDs in results — tabular data only."), kind="warn")
        else:
            _state_fips = _valid[_geo_col].str[:2].iloc[0]
            try:
                if _selected_level == "state":
                    _raw = pygris.states(cb=True, resolution="500k", cache=True)
                elif _selected_level == "county":
                    _raw = pygris.counties(state=_state_fips, cb=True, resolution="500k", cache=True)
                elif _selected_level == "tract":
                    _county_codes = _valid[_geo_col].str[2:5].unique().tolist()
                    _raw = gpd.pd.concat(
                        [pygris.tracts(state=_state_fips, county=_c, cb=True, cache=True) for _c in _county_codes],
                        ignore_index=True,
                    )
                elif _selected_level == "block_group":
                    _county_codes = _valid[_geo_col].str[2:5].unique().tolist()
                    _raw = gpd.pd.concat(
                        [pygris.block_groups(state=_state_fips, county=_c, cb=True, cache=True) for _c in _county_codes],
                        ignore_index=True,
                    )
                else:  # block
                    _county_codes = _valid[_geo_col].str[2:5].unique().tolist()
                    _raw = gpd.pd.concat(
                        [pygris.blocks(state=_state_fips, county=_c, cache=True) for _c in _county_codes],
                        ignore_index=True,
                    )
                geo_summary_gdf = _raw.to_crs("EPSG:4326").merge(
                    _agg_df, left_on="GEOID", right_on=_geo_col, how="left"
                )
            except Exception as _e:
                geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
                _status = mo.callout(mo.md(f"Could not fetch geometry: {_e}"), kind="warn")

    _status
    return (geo_summary_gdf,)


@app.cell
def _geo_summary_table_download(geo_summary_dropdown, geo_summary_gdf, io, mo, pd):
    def _to_parquet_bytes(gdf):
        buf = io.BytesIO()
        _has_geom = (
            "geometry" in gdf.columns
            and hasattr(gdf, "geometry")
            and not gdf["geometry"].isna().all()
        )
        if _has_geom:
            gdf.to_parquet(buf, index=False)
        else:
            _cols = [c for c in gdf.columns if c != "geometry"]
            pd.DataFrame(gdf[_cols]).to_parquet(buf, index=False)
        return buf.getvalue()

    _level_lbl = geo_summary_dropdown.value.replace("_", " ").title()
    _display_cols = [c for c in geo_summary_gdf.columns if c != "geometry"]

    mo.vstack([
        mo.ui.table(
            geo_summary_gdf[_display_cols].reset_index(drop=True),
            label=f"{_level_lbl} results ({len(geo_summary_gdf):,} rows)",
        ),
        mo.md("### Export"),
        mo.download(
            data=_to_parquet_bytes(geo_summary_gdf),
            filename=f"geography_{geo_summary_dropdown.value}_results.parquet",
            mimetype="application/octet-stream",
            label=f"Download {_level_lbl} Results (.parquet)",
        ),
    ])
    return


@app.cell
def _section_breakdown(breakdown_dropdown, mo):
    _sel = breakdown_dropdown.value
    _lbl = "Total (all buildings)" if _sel is None else _sel.replace("_", " ").title()
    mo.md(f"""
    ## 📊 Loss Breakdown

    Currently showing breakdown by **{_lbl}**.
    Use the *Breakdown by* dropdown above to switch dimensions.
    """)
    return


@app.cell
def _breakdown_chart(
    breakdown_dropdown,
    breakdowns_data: dict,
    comparison_level,
    mo,
    plt,
):
    _dim_col = breakdown_dropdown.value

    _output = None
    if _dim_col is None:
        _output = mo.md("_Select a breakdown dimension in the dropdown above._")
    else:
        _df = breakdowns_data[_dim_col]
        _with_results = _df[_df["aal_mean"].notna() & (_df["aal_mean"] > 0)]

        if _with_results.empty:
            _output = mo.md(f"_No results for breakdown by `{_dim_col}`._")
        else:
            # Sum across the geographic dimension → totals per breakdown value
            _grouped = (
                _with_results.groupby(_dim_col)[["aal_min", "aal_mean", "aal_max", "total_building_exposure"]]
                .sum()
                .sort_values("aal_mean", ascending=True)
            )
            _grouped["aal_ratio"] = (
                _grouped["aal_mean"]
                / _grouped["total_building_exposure"].replace(0, float("nan"))
                * 1_000_000
            )

            _fig, _ax = plt.subplots(figsize=(14, max(4, len(_grouped) * 0.6 + 1)))
            _fig.patch.set_facecolor("#f7fbff")
            _ax.set_facecolor("#f0f4f8")

            _y = range(len(_grouped))
            _bar_h = 0.55

            # Mean bars
            _colors = plt.cm.YlOrRd(
                0.25 + 0.75 * (_grouped["aal_mean"] - _grouped["aal_mean"].min())
                / (_grouped["aal_mean"].max() - _grouped["aal_mean"].min() + 1e-9)
            )
            _ax.barh(
                list(_y), _grouped["aal_mean"] / 1e6,
                height=_bar_h, color=_colors, edgecolor="white", linewidth=0.5, label="Mean AAL",
            )

            # Error bars showing min→max range
            _err_lo = (_grouped["aal_mean"] - _grouped["aal_min"]) / 1e6
            _err_hi = (_grouped["aal_max"] - _grouped["aal_mean"]) / 1e6
            _ax.errorbar(
                _grouped["aal_mean"] / 1e6,
                list(_y),
                xerr=[_err_lo.values, _err_hi.values],
                fmt="none", color="#555", linewidth=1.2, capsize=4, label="Min–Max range",
            )

            _ax.set_yticks(list(_y))
            _dim_name = _dim_col.replace('_', ' ').title()
            _ax.set_yticklabels([f"{_dim_name}: {val}" for val in _grouped.index], fontsize=9)
            #_ax.set_yticklabels(_grouped.index, fontsize=9)
            _ax.set_xlabel("AAL ($ millions)", fontsize=10)
            _ax.set_title(
                f"AAL by {_dim_col.replace('_', ' ').title()} "
                f"(summed across all {comparison_level.replace('_', ' ')}s)",
                fontsize=12, fontweight="bold",
            )
            _ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))

            def _fmt_pretty(v):
                if abs(v) >= 1e9:
                    return f"${v/1e9:.2f}B"
                if abs(v) >= 1e6:
                    return f"${v/1e6:.1f}M"
                if abs(v) >= 1e3:
                    return f"${v/1e3:.1f}k"
                return f"${v:,.0f}"

            # Bar-end labels: AAL mean value + loss ratio
            _x_max = _grouped["aal_max"].max() / 1e6
            for _yi, (_group_val, _row) in zip(_y, _grouped.iterrows()):
                _label_x = _row["aal_max"] / 1e6 + _x_max * 0.02
                _aal_lbl = _fmt_pretty(_row["aal_mean"])
                _ratio = _row["aal_ratio"]
                _ratio_lbl = f"  ({_ratio:,.0f}/M)" if _ratio == _ratio else ""  # noqa: PLR0124

                # Add `_group_val` to the front of the text string
                _ax.text(
                    _label_x, _yi,
                    f"{_group_val} - {_aal_lbl}{_ratio_lbl}",
                    va="center", ha="left", fontsize=7.5, color="#333", fontweight="bold",
                )

            # Widen right margin to fit labels
            _ax.set_xlim(right=_x_max * 1.45)

            _ax.spines["top"].set_visible(False)
            _ax.spines["right"].set_visible(False)
            _ax.legend(loc="lower right", fontsize=8)
            _fig.tight_layout()
            _output = mo.mpl.interactive(_fig)
    _output
    return


@app.cell
def _breakdown_detail_table(
    GT,
    breakdown_dropdown,
    breakdowns_data: dict,
    mo,
    pd,
):
    _dim_col = breakdown_dropdown.value

    _output = None
    if _dim_col is None:
        _output = mo.md("_Select a breakdown dimension to see the detail table._")
    else:
        _df = breakdowns_data[_dim_col]
        _with_results = _df[_df["aal_mean"].notna() & (_df["aal_mean"] > 0)]

        if _with_results.empty:
            _output = mo.md(f"_No results for breakdown by `{_dim_col}`._")
        else:
            _grouped = (
                _with_results.groupby(_dim_col)
                .agg(
                    building_count=("building_count", "sum"),
                    total_building_exposure=("total_building_exposure", "sum"),
                    aal_min=("aal_min", "sum"),
                    aal_mean=("aal_mean", "sum"),
                    aal_max=("aal_max", "sum"),
                )
                .reset_index()
                .sort_values("aal_mean", ascending=False)
                .head(15)
                .reset_index(drop=True)
            )
            _grouped["aal_ratio"] = (
                _grouped["aal_mean"]
                / _grouped["total_building_exposure"].replace(0, float("nan"))
                * 1_000_000
            )

            def _fmt_d(v):
                if pd.isna(v):
                    return "—"
                if abs(v) >= 1e9:
                    return f"${v/1e9:.2f}B"
                if abs(v) >= 1e6:
                    return f"${v/1e6:.1f}M"
                return f"${v:,.0f}"

            _display = _grouped.copy()
            _display["building_count"] = _display["building_count"].apply(
                lambda v: f"{int(v):,}" if not pd.isna(v) else "—"
            )
            _display["total_building_exposure"] = _display["total_building_exposure"].apply(_fmt_d)
            for _c in ["aal_min", "aal_mean", "aal_max"]:
                _display[_c] = _display[_c].apply(_fmt_d)
            _display["aal_ratio"] = _display["aal_ratio"].apply(
                lambda v: "—" if pd.isna(v) else f"${v:,.0f}/M"
            )

            _dim_lbl = _dim_col.replace("_", " ").title()
            _aal_cols = ["aal_min", "aal_mean", "aal_max"]

            _output = (
                GT(_display)
                .tab_header(
                    title=f"Loss Breakdown by {_dim_lbl}",
                    subtitle="Top 15 by Mean AAL — summed across all geographies",
                )
                .cols_label(
                    **{
                        _dim_col: _dim_lbl,
                        "building_count": "Buildings",
                        "total_building_exposure": "Exposure",
                        "aal_min": "AAL Min",
                        "aal_mean": "AAL Mean",
                        "aal_max": "AAL Max",
                        "aal_ratio": "AAL Ratio",
                    }
                )
                .tab_spanner(label="AAL Uncertainty Range", columns=_aal_cols)
                .tab_source_note("Ratio = USD per $1M exposure.")
            )
    _output
    return


@app.cell
def _lep_curve(mo, plt, return_periods, summary_df, summary_level):
    _output = None
    if summary_df is None:
        _output = mo.md("_No summary-level data for LEP curve._")
    else:
        _geo_col = {
            "state": "state_fips",
            "county": "county_fips",
            "tract": "tract_fips",
        }.get(summary_level, "state_fips")

        _results_rows = summary_df[
            summary_df["aal_mean"].notna() & (summary_df["aal_mean"] > 0)
        ]
        if _results_rows.empty:
            _output = mo.md("_No results for LEP curve._")
        else:
            _row = _results_rows.iloc[0]
            _geo_id = _row[_geo_col]
            _lbl = summary_level.replace("_", " ").title()

            _losses_mean = [_row.get(f"loss_rp{rp}", float("nan")) for rp in return_periods]
            # AEP in % — high frequency (RP-10 = 10%) to low frequency (RP-2000 = 0.05%)
            _probs = [1.0 / rp * 100 for rp in return_periods]

            _fig, _ax = plt.subplots(figsize=(10, 5))
            _fig.patch.set_facecolor("#f7fbff")
            _ax.set_facecolor("#f0f4f8")

            _ax.plot(
                _probs, [l / 1e6 for l in _losses_mean],
                "o-", color="#c0392b", linewidth=2.5,
                markersize=7, markerfacecolor="white", markeredgewidth=2, label="Mean loss",
            )
            _ax.fill_between(_probs, [l / 1e6 for l in _losses_mean], alpha=0.15, color="#c0392b")

            for _rp, _prob, _loss in zip(return_periods, _probs, _losses_mean):
                if _rp in (10, 100, 500) and _loss == _loss:
                    _ax.annotate(
                        f"RP-{_rp}\n${_loss/1e6:.0f}M",
                        xy=(_prob, _loss / 1e6),
                        xytext=(-8, 8), textcoords="offset points",
                        fontsize=8, color="#555", ha="right",
                    )

            _ax.set_xscale("log")
            # Invert so high-frequency (RP-10, 10% AEP) is on the LEFT
            _ax.invert_xaxis()
            _ax.set_xlabel("Annual Exceedance Probability (%) — high frequency → low frequency", fontsize=10)
            _ax.set_ylabel("Loss ($ millions)", fontsize=11)
            _ax.set_title(
                f"Loss Exceedance Probability — {_lbl} {_geo_id}",
                fontsize=13, fontweight="bold",
            )
            _ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:.0f}M"))
            _ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.3g}%"))
            _ax.grid(True, which="both", linestyle="--", alpha=0.5, color="white")
            _ax.spines["top"].set_visible(False)
            _ax.spines["right"].set_visible(False)
            _fig.tight_layout()
            _output = mo.mpl.interactive(_fig)
    _output
    return


if __name__ == "__main__":
    app.run()
