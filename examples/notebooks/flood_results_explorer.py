"""Flood Results Explorer — interactive Marimo notebook.

Visualises flood loss results from a completed InlandFloodAnalysis DuckDB run
using FloodResultsAggregator.  Primary metric is ``taal_mean`` (total AAL =
structure + content + inventory annualised average loss).

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
    import lonboard as lb
    import marimo as mo
    import numpy as np
    import pandas as pd
    import pygris
    from great_tables import GT, loc, style
    from lonboard.colormap import apply_continuous_cmap

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from inland_consequences.results_aggregation import FloodResultsAggregator

    return (
        FloodResultsAggregator,
        Path,
        apply_continuous_cmap,
        duckdb,
        gpd,
        io,
        lb,
        mo,
        np,
        pd,
        pygris,
    )


@app.cell
def _header(mo):
    mo.md(r"""
    # 🌊 Flood Results Explorer

    Aggregated inland flood loss results from a completed `InlandFloodAnalysis` run.
    The primary metric is **`taal_mean`** — total Average Annual Loss (structure +
    content + inventory combined).  Use the controls below to select a geography
    level and map metric.  For attribute breakdowns, see the **Breakdown Analysis**
    section below the map.
    """)
    return


@app.cell
def _db_picker(Path, mo):
    _root = Path(__file__).parent.parent
    _excluded_dirs = {"tests", "outputs"}

    _candidates = []
    for _p in sorted(_root.rglob("*.duckdb"), reverse=True):
        _rel_parts = set(_p.relative_to(_root).parts[:-1])
        if _rel_parts & _excluded_dirs:
            continue
        if _p.name.startswith("test_"):
            continue
        _candidates.append(_p)

    _db_options = {str(_p.relative_to(_root)): _p for _p in _candidates}
    _db_default = next(iter(_db_options)) if _db_options else None

    db_file_dropdown = mo.ui.dropdown(
        options=_db_options,
        value=_db_default,
        label="DuckDB file",
    )
    view_button = mo.ui.run_button(label="▶ View Results")

    mo.vstack([
        mo.md("### Configure Analysis"),
        db_file_dropdown,
        view_button,
    ])
    return db_file_dropdown, view_button


@app.cell
def _config_gate(db_file_dropdown, mo, view_button):
    mo.stop(
        not view_button.value,
        mo.callout(
            mo.md("Select a DuckDB file, then click **▶ View Results**."),
            kind="info",
        ),
    )
    DB_PATH = db_file_dropdown.value
    return (DB_PATH,)


@app.cell
def _overall_metrics(DB_PATH, mo):
    def _fmt_money(v):
        if v is None or (isinstance(v, float) and v != v):
            return "N/A"
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v/1e3:.0f}k"
        return f"${v:,.0f}"

    _conn = None
    try:
        _conn = __import__("duckdb").connect(str(DB_PATH), read_only=True)

        _bldg_count = _conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        _bldg_exp = _conn.execute("SELECT SUM(building_cost) FROM buildings").fetchone()[0]
        _cont_exp = _conn.execute("SELECT SUM(content_cost) FROM buildings").fetchone()[0]
        _taal_mean = _conn.execute("SELECT SUM(taal_mean) FROM aal_losses").fetchone()[0]
        _taal_max = _conn.execute("SELECT SUM(taal_max) FROM aal_losses").fetchone()[0]
        _avg_taal = (_taal_mean / _bldg_count) if (_taal_mean is not None and _bldg_count) else None
        _rps = _conn.execute(
            "SELECT DISTINCT return_period FROM losses ORDER BY return_period"
        ).fetchdf()["return_period"].astype(int).tolist()
        _rp_str = ", ".join(str(r) for r in _rps)
    finally:
        if _conn is not None:
            _conn.close()

    _tiles = mo.hstack([
        mo.stat(value=f"{_bldg_count:,}", label="Total Buildings", bordered=True),
        mo.stat(value=_fmt_money(_bldg_exp), label="Building Exposure", bordered=True),
        mo.stat(value=_fmt_money(_cont_exp), label="Content Exposure", bordered=True),
        mo.stat(value=_fmt_money(_taal_mean), label="Total TAAL Mean", bordered=True),
        mo.stat(value=_fmt_money(_taal_max), label="Total TAAL Max", bordered=True),
        mo.stat(value=_fmt_money(_avg_taal), label="Avg TAAL / Building", bordered=True),
        mo.stat(value=_rp_str, label="Return Periods (yr)", bordered=True),
    ])
    _tiles
    return


@app.cell
def _agg_controls(mo):
    geo_dropdown = mo.ui.dropdown(
        options={
            "State": "state",
            "County": "county",
            "Tract": "tract",
            "Block Group": "block_group",
            "Block": "block",
            "Community": "community",
            "HUC (Watershed)": "huc",
        },
        value="County",
        label="Geography",
    )
    metric_dropdown = mo.ui.dropdown(
        options={
            "TAAL Mean ($)": "taal_mean",
            "TAAL Min ($)": "taal_min",
            "TAAL Max ($)": "taal_max",
            "TAAL Ratio ($/M)": "taal_ratio",
            "AAL Mean ($)": "aal_mean",
            "AAL Ratio ($/M)": "aal_ratio",
        },
        value="TAAL Mean ($)",
        label="Map metric",
    )

    mo.hstack([geo_dropdown, metric_dropdown], gap=2)
    return geo_dropdown, metric_dropdown


@app.cell
def _agg_data(
    DB_PATH,
    FloodResultsAggregator,
    duckdb,
    geo_dropdown,
    gpd,
    mo,
    pygris,
):
    import requests as _requests
    from shapely.geometry import shape as _shape

    _geo_level = geo_dropdown.value

    _conn = duckdb.connect(str(DB_PATH), read_only=True)
    _agg = FloodResultsAggregator(conn=_conn)
    _agg_df = _agg.aggregate(
        geography=_geo_level,
        breakdown=[],
    )
    return_periods = _agg.get_return_periods()
    _conn.close()

    # --- Geometry fetch helpers ---
    _CENSUS_GEO_COL = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
    }

    _status = None
    geo_summary_gdf = None

    if _geo_level == "huc":
        _huc_ids = _agg_df["huc"].dropna().unique().tolist() if "huc" in _agg_df.columns else []
        _rows = []
        if _huc_ids:
            _BASE_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
            _batches = [_huc_ids[i: i + 50] for i in range(0, len(_huc_ids), 50)]
            for _batch in mo.status.progress_bar(
                _batches,
                title="Downloading HUC8 boundaries (USGS WBD)…",
                remove_on_exit=True,
            ):
                try:
                    _ids_str = ",".join(f"'{h}'" for h in _batch)
                    _resp = _requests.get(_BASE_URL, params={
                        "where": f"huc8 IN ({_ids_str})",
                        "outFields": "huc8,name",
                        "returnGeometry": "true",
                        "f": "geojson",
                        "outSR": "4326",
                    }, timeout=30)
                    _resp.raise_for_status()
                    for _feat in _resp.json().get("features", []):
                        _props = _feat.get("properties") or _feat.get("attributes") or {}
                        _geom = _shape(_feat["geometry"]) if _feat.get("geometry") else None
                        _rows.append({**_props, "geometry": _geom})
                except Exception:
                    pass
        if _rows:
            _huc_gdf = gpd.GeoDataFrame(_rows, crs="EPSG:4326")
            _huc_gdf.columns = [c.lower() for c in _huc_gdf.columns]
            _huc_gdf = _huc_gdf.rename(columns={"huc8": "huc", "name": "huc_name"})
            geo_summary_gdf = gpd.GeoDataFrame(
                _agg_df.merge(_huc_gdf[["huc", "huc_name", "geometry"]], on="huc", how="left"),
                geometry="geometry", crs="EPSG:4326",
            )
        else:
            geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
            _status = mo.callout(mo.md("Could not fetch HUC8 boundaries — tabular data only."), kind="warn")

    elif _geo_level == "community":
        _comm_ids = _agg_df["community_id"].dropna().unique().tolist() if "community_id" in _agg_df.columns else []
        _rows = []
        if _comm_ids:
            _LAYER_URL = "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/NFIP_Community_Layer__flattened__2024v1_WFL1/FeatureServer/0/query"
            _batches = [_comm_ids[i: i + 50] for i in range(0, len(_comm_ids), 50)]
            for _batch in mo.status.progress_bar(
                _batches,
                title="Fetching NFIP community shapes…",
                remove_on_exit=True,
            ):
                try:
                    _ids_str = ",".join(f"'{c}'" for c in _batch)
                    _resp = _requests.get(_LAYER_URL, params={
                        "where": f"cis_cid IN ({_ids_str})",
                        "outFields": "cis_cid,cis_community_name_short",
                        "returnGeometry": "true",
                        "f": "geojson",
                        "outSR": "4326",
                    }, timeout=30)
                    _resp.raise_for_status()
                    for _feat in _resp.json().get("features", []):
                        _props = _feat.get("properties") or _feat.get("attributes") or {}
                        _geom = _shape(_feat["geometry"]) if _feat.get("geometry") else None
                        _rows.append({**_props, "geometry": _geom})
                except Exception:
                    pass
        if _rows:
            _comm_gdf = gpd.GeoDataFrame(_rows, crs="EPSG:4326")
            _comm_gdf.columns = [c.lower() for c in _comm_gdf.columns]
            _comm_gdf = _comm_gdf.rename(columns={"cis_cid": "community_id", "cis_community_name_short": "community_name"})
            geo_summary_gdf = gpd.GeoDataFrame(
                _agg_df.merge(_comm_gdf[["community_id", "community_name", "geometry"]], on="community_id", how="left"),
                geometry="geometry", crs="EPSG:4326",
            )
        else:
            geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
            _status = mo.callout(mo.md("Could not fetch community boundaries — tabular data only."), kind="warn")

    elif _geo_level in _CENSUS_GEO_COL:
        _geo_col = _CENSUS_GEO_COL[_geo_level]
        _valid = _agg_df[_agg_df[_geo_col].notna()] if _geo_col in _agg_df.columns else _agg_df
        if _valid.empty:
            geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
            _status = mo.callout(mo.md("No geography IDs in results — tabular data only."), kind="warn")
        else:
            _state_fips = _valid[_geo_col].str[:2].iloc[0]
            try:
                if _geo_level == "state":
                    _raw = pygris.states(cb=True, resolution="500k", cache=True)
                elif _geo_level == "county":
                    _raw = pygris.counties(state=_state_fips, cb=True, resolution="500k", cache=True)
                elif _geo_level == "tract":
                    _county_codes = _valid[_geo_col].str[2:5].unique().tolist()
                    _raw = gpd.pd.concat(
                        [pygris.tracts(state=_state_fips, county=_c, cb=True, cache=True) for _c in _county_codes],
                        ignore_index=True,
                    )
                elif _geo_level == "block_group":
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
    else:
        geo_summary_gdf = gpd.GeoDataFrame(_agg_df)
        _status = mo.callout(
            mo.md(f"No census geometry available for **{_geo_level}** — tabular data only."),
            kind="warn",
        )

    _status
    return (geo_summary_gdf,)


@app.cell
def _lonboard_map(
    apply_continuous_cmap,
    geo_summary_gdf,
    gpd,
    lb,
    metric_dropdown,
    mo,
    np,
):
    import matplotlib.cm as _mcm

    _metric_col = metric_dropdown.value
    _has_geom = (
        "geometry" in geo_summary_gdf.columns
        and not geo_summary_gdf["geometry"].isna().all()
    )
    _has_metric = _metric_col in geo_summary_gdf.columns

    _map_out = None
    if _has_geom and _has_metric:
        _keep_cols = [c for c in geo_summary_gdf.columns
                      if c in {"geometry", _metric_col, "taal_mean", "building_count",
                               "county_fips", "tract_fips", "state_fips", "block_group_fips",
                               "huc", "huc_name", "community_id", "community_name"}]
        _gdf = geo_summary_gdf[_keep_cols].copy()
        _gdf = _gdf[_gdf["geometry"].notna() & _gdf[_metric_col].notna() & (_gdf[_metric_col] > 0)].copy()
        _gdf = gpd.GeoDataFrame(_gdf, geometry="geometry", crs="EPSG:4326").reset_index(drop=True)

        if _gdf.empty:
            _map_out = mo.callout(
                mo.md(f"No rows with both **geometry** and **{_metric_col} > 0** to map."),
                kind="info",
            )
        else:
            _vals = _gdf[_metric_col].fillna(0).values.astype(float)
            _vals_log = np.log1p(_vals)
            _vmax_log = _vals_log.max()
            _normalized = (
                (_vals_log / _vmax_log).clip(0, 1) if _vmax_log > 0 else np.zeros_like(_vals_log)
            )
            _fill_colors = apply_continuous_cmap(_normalized, _mcm.YlOrRd, alpha=0.85)

            _layer = lb.PolygonLayer.from_geopandas(
                _gdf,
                get_fill_color=_fill_colors,
                get_line_color=[60, 60, 60, 80],
                get_line_width=50,
                pickable=True,
                auto_highlight=True,
            )
            _map_out = mo.ui.anywidget(lb.Map(layers=[_layer], height=500))
    else:
        _map_out = mo.callout(mo.md("No geometry available for the selected level — see table below."), kind="info")

    _map_out
    return


@app.cell
def _agg_table_download(
    geo_dropdown,
    geo_summary_gdf,
    io,
    mo,
    pd,
):
    def _fmt_money(v):
        if v is None or (isinstance(v, float) and v != v):
            return "N/A"
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v/1e3:.0f}k"
        return f"${v:,.0f}"

    _level_lbl = geo_dropdown.value.replace("_", " ").title()

    _display = geo_summary_gdf[[c for c in geo_summary_gdf.columns if c != "geometry"]].copy()

    # Summary stats on rows with positive taal_mean
    _with_results = pd.DataFrame()
    if "taal_mean" in _display.columns:
        _with_results = _display[_display["taal_mean"].notna() & (_display["taal_mean"] > 0)]

    _total_taal = _with_results["taal_mean"].sum() if not _with_results.empty else None
    _total_bldgs = (
        int(_with_results["building_count"].sum())
        if "building_count" in _with_results.columns and not _with_results.empty
        else None
    )
    _avg_taal = (
        _total_taal / _total_bldgs
        if _total_taal is not None and _total_bldgs and _total_bldgs > 0
        else None
    )

    _sort_col = "taal_mean" if "taal_mean" in _display.columns else _display.columns[0]
    _display = _display.sort_values(_sort_col, ascending=False).reset_index(drop=True)

    def _to_parquet_bytes(gdf):
        import geopandas as _gpd
        _buf = io.BytesIO()
        _hg = (
            "geometry" in gdf.columns
            and not gdf["geometry"].isna().all()
        )
        if _hg:
            if not isinstance(gdf, _gpd.GeoDataFrame):
                gdf = _gpd.GeoDataFrame(gdf, geometry="geometry")
            gdf.to_parquet(_buf, index=False)
        else:
            _cols = [c for c in gdf.columns if c != "geometry"]
            pd.DataFrame(gdf[_cols]).to_parquet(_buf, index=False)
        return _buf.getvalue()

    _filename = f"agg_{geo_dropdown.value}.parquet"

    mo.vstack([
        mo.hstack([
            mo.stat(value=_fmt_money(_total_taal), label=f"Total TAAL Mean ({len(_with_results)} units)", bordered=True),
            mo.stat(value=f"{_total_bldgs:,}" if _total_bldgs else "N/A", label="Total Buildings", bordered=True),
            mo.stat(value=_fmt_money(_avg_taal), label="Avg TAAL / Building", bordered=True),
        ]),
        mo.ui.table(_display, label=f"{_level_lbl} aggregated results ({len(geo_summary_gdf):,} rows)"),
        mo.download(
            data=_to_parquet_bytes(geo_summary_gdf),
            filename=_filename,
            mimetype="application/octet-stream",
            label=f"Download {_level_lbl} Results (.parquet)",
        ),
    ])
    return


@app.cell
def _breakdown_section_header(mo):
    mo.md(r"""
    ## 📊 Breakdown Analysis

    Analyse total AAL and building exposure broken down by a building attribute
    across a chosen geography level.  **Metrics only** — no geometry is fetched.
    Results include a summary table by attribute category (Great Tables) and a
    full geo × breakdown tabular view.
    """)
    return


@app.cell
def _breakdown_controls(mo):
    breakdown_geo_dropdown = mo.ui.dropdown(
        options={
            "State": "state",
            "County": "county",
            "Tract": "tract",
            "Block Group": "block_group",
            "Block": "block",
            "Community": "community",
            "HUC (Watershed)": "huc",
        },
        value="County",
        label="Geography",
    )
    breakdown_col_dropdown = mo.ui.dropdown(
        options={
            "Occupancy Type": "occupancy_type",
            "Damage Category": "st_damcat",
            "Building Type": "general_building_type",
            "Foundation Type": "foundation_type",
            "Flood Peril Type": "flood_peril_type",
        },
        value="Occupancy Type",
        label="Breakdown by",
    )
    breakdown_run_button = mo.ui.run_button(label="▶ Run Breakdown")

    mo.hstack([breakdown_geo_dropdown, breakdown_col_dropdown, breakdown_run_button], gap=2)
    return breakdown_col_dropdown, breakdown_geo_dropdown, breakdown_run_button


@app.cell
def _breakdown_data(
    DB_PATH,
    FloodResultsAggregator,
    breakdown_col_dropdown,
    breakdown_geo_dropdown,
    breakdown_run_button,
    duckdb,
    mo,
):
    mo.stop(
        not breakdown_run_button.value,
        mo.callout(
            mo.md("Select a geography level and breakdown attribute, then click **▶ Run Breakdown**."),
            kind="info",
        ),
    )

    _geo_level_bd = breakdown_geo_dropdown.value
    _breakdown_col_bd = breakdown_col_dropdown.value

    _conn_bd = duckdb.connect(str(DB_PATH), read_only=True)
    _agg_bd = FloodResultsAggregator(conn=_conn_bd)
    breakdown_df = _agg_bd.aggregate(
        geography=_geo_level_bd,
        breakdown=[_breakdown_col_bd],
    )
    _conn_bd.close()

    return (breakdown_df,)


@app.cell
def _breakdown_display(
    GT,
    breakdown_col_dropdown,
    breakdown_df,
    breakdown_geo_dropdown,
    io,
    loc,
    mo,
    pd,
    style,
):
    _breakdown_col = breakdown_col_dropdown.value
    _geo_lbl = breakdown_geo_dropdown.value.replace("_", " ").title()
    _geo_id_col = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
        "community": "community_id",
        "huc": "huc",
    }.get(breakdown_geo_dropdown.value, "geo_id")

    # --- Column inventories ---
    _money_cols = [
        "total_building_exposure", "total_content_exposure", "total_exposure",
        "aal_mean", "taal_min", "taal_mean", "taal_max",
    ]
    _ratio_cols = ["aal_ratio", "taal_ratio"]
    _count_cols = ["building_count"]

    _avail_money = [c for c in _money_cols if c in breakdown_df.columns]
    _avail_ratio = [c for c in _ratio_cols if c in breakdown_df.columns]
    _avail_count = [c for c in _count_cols if c in breakdown_df.columns]

    # --- 1. Great Tables summary: collapse to breakdown category only ---
    _agg_ops = {}
    for _mc in _avail_count:
        _agg_ops[_mc] = "sum"
    for _mc in _avail_money:
        _agg_ops[_mc] = "sum"
    for _mc in _avail_ratio:
        _agg_ops[_mc] = "mean"

    _sort_key = "taal_mean" if "taal_mean" in _agg_ops else (list(_agg_ops.keys())[0] if _agg_ops else _breakdown_col)
    _summary_df = (
        breakdown_df
        .dropna(subset=[_breakdown_col])
        .groupby(_breakdown_col, as_index=False)
        .agg(_agg_ops)
        .sort_values(_sort_key, ascending=False)
        .reset_index(drop=True)
    )

    _gt_show_cols = [_breakdown_col] + [
        c for c in ["building_count", "total_building_exposure", "taal_mean", "taal_ratio"]
        if c in _summary_df.columns
    ]
    _gt_df = _summary_df[_gt_show_cols].copy()

    _gt = GT(_gt_df, rowname_col=_breakdown_col).tab_header(
        title=f"Total AAL by {_breakdown_col.replace('_', ' ').title()}",
        subtitle=f"Summed across all {_geo_lbl} units with losses",
    )

    _col_labels = {
        "building_count": "Buildings",
        "total_building_exposure": "Building Exposure ($)",
        "taal_mean": "Total AAL Mean ($)",
        "taal_ratio": "AAL Ratio ($/M Exp.)",
    }
    _gt = _gt.cols_label(**{k: v for k, v in _col_labels.items() if k in _gt_df.columns})

    for _fmt_col in ["total_building_exposure", "taal_mean"]:
        if _fmt_col in _gt_df.columns:
            _gt = _gt.fmt_currency(columns=_fmt_col, currency="USD", use_subunits=False)
    if "taal_ratio" in _gt_df.columns:
        _gt = _gt.fmt_number(columns="taal_ratio", decimals=2)
    if "building_count" in _gt_df.columns:
        _gt = _gt.fmt_integer(columns="building_count")
    if "taal_mean" in _gt_df.columns:
        _gt = _gt.data_color(
            columns="taal_mean",
            palette=["#FFFFFF", "#FF6B35"],
            na_color="#EEEEEE",
        )

    # --- 2. Full geo × breakdown tabular results ---
    _full_cols = (
        [c for c in [_geo_id_col, _breakdown_col] if c in breakdown_df.columns]
        + [
            c for c in [
                "building_count", "total_building_exposure",
                "taal_min", "taal_mean", "taal_max", "taal_ratio",
                "aal_mean", "aal_ratio",
            ]
            if c in breakdown_df.columns
        ]
    )
    _full_df = (
        breakdown_df[_full_cols]
        .sort_values(
            [_geo_id_col, "taal_mean"] if "taal_mean" in breakdown_df.columns else [_geo_id_col],
            ascending=[True, False] if "taal_mean" in breakdown_df.columns else [True],
        )
        .reset_index(drop=True)
    )

    # --- Download ---
    _dl_buf = io.BytesIO()
    breakdown_df[[c for c in breakdown_df.columns if c != "geometry"]].to_parquet(_dl_buf, index=False)
    _dl_filename = f"breakdown_{breakdown_geo_dropdown.value}_{_breakdown_col}.parquet"

    mo.vstack([
        mo.md(f"### By {_breakdown_col.replace('_', ' ').title()} — Summary"),
        _gt,
        mo.md(f"### {_geo_lbl} × {_breakdown_col.replace('_', ' ').title()} — Full Results"),
        mo.ui.table(_full_df, label=f"{len(breakdown_df):,} rows"),
        mo.download(
            data=_dl_buf.getvalue(),
            filename=_dl_filename,
            mimetype="application/octet-stream",
            label="Download Breakdown Results (.parquet)",
        ),
    ])
    return


@app.cell
def _wide_section_header(mo):
    mo.md(r"""
    ## 📦 Wide Results Export

    Build a building-level wide-format dataset by joining all selected tables
    onto the `buildings` base.  Pivoted tables (hazard, losses, damage function
    statistics) are spread one column per return period.  Download the result as
    a GeoParquet file for use in GIS or further analysis.
    """)
    return


@app.cell
def _wide_controls(mo):
    _ALL_TABLES = [
        "hazard",
        "losses",
        "damage_function_statistics",
        "content_damage_function_statistics",
        "inventory_damage_function_statistics",
        "structure_damage_functions",
        "content_damage_functions",
        "inventory_damage_functions",
        "aal_losses",
    ]

    wide_table_checkboxes = mo.ui.multiselect(
        options=_ALL_TABLES,
        value=_ALL_TABLES,
        label="Tables to include (buildings is always the base)",
    )
    wide_generate_button = mo.ui.run_button(label="▶ Generate Wide Results")

    mo.vstack([
        mo.callout(
            mo.md(
                "Select which tables to join onto `buildings`.  "
                "Pivoted tables are spread one column per return period.  "
                "Large selections may take a moment."
            ),
            kind="info",
        ),
        wide_table_checkboxes,
        wide_generate_button,
    ])
    return wide_generate_button, wide_table_checkboxes


@app.cell
def _wide_generate(
    DB_PATH,
    duckdb,
    io,
    mo,
    wide_generate_button,
    wide_table_checkboxes,
):
    mo.stop(
        not wide_generate_button.value,
        mo.callout(mo.md("Select tables and click **▶ Generate Wide Results**."), kind="info"),
    )

    import geopandas as _gpd
    from shapely import wkb as _wkb

    _selected = list(wide_table_checkboxes.value)

    # Detect return periods dynamically
    _conn = duckdb.connect(str(DB_PATH), read_only=True)
    _conn.execute("INSTALL spatial; LOAD spatial;")
    _rps = _conn.execute(
        "SELECT DISTINCT return_period FROM losses ORDER BY return_period"
    ).fetchdf()["return_period"].astype(int).tolist()
    _conn.close()

    # --- Build dynamic SQL parts ---
    _ctes = []
    _joins = []
    _select_cols = [
        "b.id", "b.bid", "b.cbfips", "b.st_damcat", "b.occupancy_type",
        "b.general_building_type", "b.number_stories", "b.area",
        "b.first_floor_height", "b.med_yr_blt", "b.building_cost",
        "b.content_cost", "b.val_vehic", "b.ftprntid", "b.ftprntsrc",
        "b.source", "b.students", "b.pop2amu65", "b.pop2amo65",
        "b.pop2pmu65", "b.pop2pmo65", "b.o65disable", "b.u65disable",
        "b.x", "b.y", "b.firmzone", "b.grnd_elv_m", "b.ground_elv",
        "b.foundation_type", "b.flood_peril_type", "b.geometry",
    ]

    if "structure_damage_functions" in _selected:
        _ctes.append("""    struct_ddf AS (
        SELECT building_id,
               FIRST(damage_function_id ORDER BY weight DESC) AS struct_ddf_id,
               FIRST(first_floor_height  ORDER BY weight DESC) AS struct_ffh,
               FIRST(ffh_sig            ORDER BY weight DESC) AS struct_ffh_sig,
               FIRST(weight             ORDER BY weight DESC) AS struct_ddf_weight
        FROM structure_damage_functions GROUP BY building_id
    )""")
        _joins.append("LEFT JOIN struct_ddf sd ON b.id = sd.building_id")
        _select_cols += ["sd.struct_ddf_id", "sd.struct_ffh", "sd.struct_ffh_sig", "sd.struct_ddf_weight"]

    if "content_damage_functions" in _selected:
        _ctes.append("""    content_ddf AS (
        SELECT building_id,
               MAX(damage_function_id) AS content_ddf_id,
               MAX(weight)             AS content_ddf_weight
        FROM content_damage_functions GROUP BY building_id
    )""")
        _joins.append("LEFT JOIN content_ddf cd ON b.id = cd.building_id")
        _select_cols += ["cd.content_ddf_id", "cd.content_ddf_weight"]

    if "inventory_damage_functions" in _selected:
        _ctes.append("""    inventory_ddf AS (
        SELECT building_id,
               MAX(damage_function_id) AS inventory_ddf_id,
               MAX(weight)             AS inventory_ddf_weight
        FROM inventory_damage_functions GROUP BY building_id
    )""")
        _joins.append("LEFT JOIN inventory_ddf id_ ON b.id = id_.building_id")
        _select_cols += ["id_.inventory_ddf_id", "id_.inventory_ddf_weight"]

    if "hazard" in _selected:
        _hz_parts = []
        for _rp in _rps:
            _hz_parts += [
                f"MAX(depth)    FILTER (WHERE return_period = {_rp}) AS depth_rp{_rp}",
                f"MAX(std_dev)  FILTER (WHERE return_period = {_rp}) AS depth_std_dev_rp{_rp}",
                f"MAX(velocity) FILTER (WHERE return_period = {_rp}) AS velocity_rp{_rp}",
                f"MAX(duration) FILTER (WHERE return_period = {_rp}) AS duration_rp{_rp}",
            ]
        _ctes.append(
            "    hazard_wide AS (\n"
            "        SELECT id,\n               "
            + ",\n               ".join(_hz_parts)
            + "\n        FROM hazard GROUP BY id\n    )"
        )
        _joins.append("LEFT JOIN hazard_wide hw ON b.id = hw.id")
        for _rp in _rps:
            _select_cols += [
                f"hw.depth_rp{_rp}", f"hw.depth_std_dev_rp{_rp}",
                f"hw.velocity_rp{_rp}", f"hw.duration_rp{_rp}",
            ]

    if "losses" in _selected:
        _loss_fields = [
            "loss_min", "loss_mode_clamped", "loss_mean", "loss_mean_adjusted",
            "loss_std", "loss_max",
            "content_loss_min", "content_loss_mean", "content_loss_max",
            "inventory_loss_min", "inventory_loss_mean", "inventory_loss_max",
            "total_loss_min", "total_loss_mean", "total_loss_max",
        ]
        _lw_parts = []
        for _rp in _rps:
            for _f in _loss_fields:
                _lw_parts.append(
                    f"MAX({_f}) FILTER (WHERE return_period = {_rp}) AS {_f}_rp{_rp}"
                )
        _ctes.append(
            "    losses_wide AS (\n"
            "        SELECT id,\n               "
            + ",\n               ".join(_lw_parts)
            + "\n        FROM losses GROUP BY id\n    )"
        )
        _joins.append("LEFT JOIN losses_wide lw ON b.id = lw.id")
        for _rp in _rps:
            for _f in _loss_fields:
                _select_cols.append(f"lw.{_f}_rp{_rp}")

    if "damage_function_statistics" in _selected:
        _dfs_fields = [
            "damage_percent", "d_min", "d_max", "d_mode",
            "damage_percent_mean", "damage_percent_std",
            "triangular_std_dev", "range_std_dev",
        ]
        _dfs_aliases = [
            "dmg_pct", "dmg_d_min", "dmg_d_max", "dmg_d_mode",
            "dmg_pct_mean", "dmg_pct_std", "dmg_tri_std", "dmg_range_std",
        ]
        _dfs_parts = []
        for _rp in _rps:
            for _f, _a in zip(_dfs_fields, _dfs_aliases):
                _dfs_parts.append(
                    f"MAX({_f}) FILTER (WHERE return_period = {_rp}) AS {_a}_rp{_rp}"
                )
        _ctes.append(
            "    dfs_wide AS (\n"
            "        SELECT building_id,\n               "
            + ",\n               ".join(_dfs_parts)
            + "\n        FROM damage_function_statistics GROUP BY building_id\n    )"
        )
        _joins.append("LEFT JOIN dfs_wide dfs ON b.id = dfs.building_id")
        for _rp in _rps:
            for _a in _dfs_aliases:
                _select_cols.append(f"dfs.{_a}_rp{_rp}")

    if "content_damage_function_statistics" in _selected:
        _cdfs_fields = [
            "damage_percent", "d_min", "d_max", "d_mode",
            "damage_percent_mean", "damage_percent_std",
        ]
        _cdfs_aliases = [
            "cdfs_dmg_pct", "cdfs_d_min", "cdfs_d_max", "cdfs_d_mode",
            "cdfs_dmg_pct_mean", "cdfs_dmg_pct_std",
        ]
        _cdfs_parts = []
        for _rp in _rps:
            for _f, _a in zip(_cdfs_fields, _cdfs_aliases):
                _cdfs_parts.append(
                    f"MAX({_f}) FILTER (WHERE return_period = {_rp}) AS {_a}_rp{_rp}"
                )
        _ctes.append(
            "    cdfs_wide AS (\n"
            "        SELECT building_id,\n               "
            + ",\n               ".join(_cdfs_parts)
            + "\n        FROM content_damage_function_statistics GROUP BY building_id\n    )"
        )
        _joins.append("LEFT JOIN cdfs_wide cdfs ON b.id = cdfs.building_id")
        for _rp in _rps:
            for _a in _cdfs_aliases:
                _select_cols.append(f"cdfs.{_a}_rp{_rp}")

    if "inventory_damage_function_statistics" in _selected:
        _idfs_fields = [
            "damage_percent", "d_min", "d_max", "d_mode",
            "damage_percent_mean", "damage_percent_std",
        ]
        _idfs_aliases = [
            "idfs_dmg_pct", "idfs_d_min", "idfs_d_max", "idfs_d_mode",
            "idfs_dmg_pct_mean", "idfs_dmg_pct_std",
        ]
        _idfs_parts = []
        for _rp in _rps:
            for _f, _a in zip(_idfs_fields, _idfs_aliases):
                _idfs_parts.append(
                    f"MAX({_f}) FILTER (WHERE return_period = {_rp}) AS {_a}_rp{_rp}"
                )
        _ctes.append(
            "    idfs_wide AS (\n"
            "        SELECT building_id,\n               "
            + ",\n               ".join(_idfs_parts)
            + "\n        FROM inventory_damage_function_statistics GROUP BY building_id\n    )"
        )
        _joins.append("LEFT JOIN idfs_wide idfs ON b.id = idfs.building_id")
        for _rp in _rps:
            for _a in _idfs_aliases:
                _select_cols.append(f"idfs.{_a}_rp{_rp}")

    if "aal_losses" in _selected:
        _joins.append("LEFT JOIN aal_losses al ON b.id = al.id")
        _select_cols += [
            "al.baal_min", "al.baal_mean", "al.baal_std", "al.baal_max",
            "al.caal_min", "al.caal_mean", "al.caal_max",
            "al.iaal_min", "al.iaal_mean", "al.iaal_max",
            "al.taal_min", "al.taal_mean", "al.taal_max",
            "al.baalr", "al.caalr", "al.iaalr", "al.taalr",
        ]

    # Assemble WHERE clause
    _where = "WHERE al.taal_mean > 0" if "aal_losses" in _selected else ""

    # Assemble full SQL
    _cte_block = ""
    if _ctes:
        _cte_block = "WITH\n" + ",\n".join(_ctes) + "\n\n"

    _wide_sql = (
        "INSTALL spatial; LOAD spatial;\n\n"
        + _cte_block
        + "SELECT\n    "
        + ",\n    ".join(_select_cols)
        + "\nFROM buildings b\n"
        + "\n".join(_joins)
        + ("\n" + _where if _where else "")
    )

    # Execute
    _conn2 = duckdb.connect(str(DB_PATH), read_only=True)
    _conn2.execute("INSTALL spatial; LOAD spatial;")
    _result_df = _conn2.execute(
        "\n".join(_wide_sql.strip().splitlines()[2:])  # skip the INSTALL/LOAD lines already done
    ).df()
    _conn2.close()

    # Convert geometry bytes (WKB) → shapely
    if "geometry" in _result_df.columns and len(_result_df) > 0:
        _sample = _result_df["geometry"].dropna()
        if len(_sample) > 0 and isinstance(_sample.iloc[0], (bytes, bytearray)):
            _result_df["geometry"] = _result_df["geometry"].apply(
                lambda x: _wkb.loads(x) if x is not None else None
            )
    result_wide_gdf = _gpd.GeoDataFrame(_result_df, geometry="geometry", crs="EPSG:4326")

    # Download bytes
    _buf = io.BytesIO()
    result_wide_gdf.to_parquet(_buf, index=False)

    mo.vstack([
        mo.stat(value=f"{len(result_wide_gdf):,}", label="Buildings in wide results", bordered=True),
        mo.download(
            data=_buf.getvalue(),
            filename="wide_results.parquet",
            mimetype="application/octet-stream",
            label="Download Wide Results (.parquet)",
        ),
    ])
    return


if __name__ == "__main__":
    app.run()
