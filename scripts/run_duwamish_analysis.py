"""
Run inland flood analysis for the Duwamish watershed and export results
to a wide-format GeoParquet file.

Usage:
    uv run python scripts/run_duwamish_analysis.py
"""

import sys
import os
from pathlib import Path

# src/ layout: add the repo's src directory so inland_consequences is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import duckdb
import geopandas as gpd

from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.inland_vulnerability import InlandFloodVulnerability
from inland_consequences.nsi_buildings import NsiBuildings
from inland_consequences.raster_collection import RasterCollection
from sphere.flood.single_value_reader import SingleValueRaster

# =============================================================================
# Paths
# =============================================================================

DEPTH_DIR = Path(
    r"E:\projects\Inland\Duwamish_AEP_MeanGrids_100225"
    r"\model-library\ffrd-duwamish\production\simulations\aep-grids\aep-grids-update"
)
STD_DIR = Path(
    r"E:\projects\Inland\Duwamish_AEP_STDGrids_100225"
    r"\model-library\ffrd-duwamish\production\simulations\aep-grids\aep-grids-update"
)
NSI_GPKG = Path(r"E:\projects\Inland\nsi_2022_53.gpkg")
OUTPUT_PARQUET = Path("results_wide_duwamish.parquet")

RETURN_PERIODS = [10, 20, 50, 100, 200, 500, 1000, 2000]


# =============================================================================
# Build raster collection
# =============================================================================

def build_raster_collection() -> RasterCollection:
    rp_map = {}
    for rp in RETURN_PERIODS:
        rp_map[rp] = {
            "depth":       SingleValueRaster(str(DEPTH_DIR / f"aep_mean_depth_{rp}yr.tif")),
            "velocity":    SingleValueRaster(str(DEPTH_DIR / f"aep_mean_velocity_{rp}yr.tif")),
            "uncertainty": SingleValueRaster(str(STD_DIR  / f"aep_stdev_depth_{rp}yr.tif")),
        }
    return RasterCollection(rp_map)


# =============================================================================
# Wide-format SQL (pivots hazard, damage, losses across 8 return periods)
# =============================================================================

WIDE_SQL = r"""
INSTALL spatial;
LOAD spatial;

COPY (
    WITH
    hazard_wide AS (
        SELECT
            id,
            MAX(depth)   FILTER (WHERE return_period =   10) AS depth_rp10,
            MAX(depth)   FILTER (WHERE return_period =   20) AS depth_rp20,
            MAX(depth)   FILTER (WHERE return_period =   50) AS depth_rp50,
            MAX(depth)   FILTER (WHERE return_period =  100) AS depth_rp100,
            MAX(depth)   FILTER (WHERE return_period =  200) AS depth_rp200,
            MAX(depth)   FILTER (WHERE return_period =  500) AS depth_rp500,
            MAX(depth)   FILTER (WHERE return_period = 1000) AS depth_rp1000,
            MAX(depth)   FILTER (WHERE return_period = 2000) AS depth_rp2000,

            MAX(std_dev) FILTER (WHERE return_period =   10) AS depth_std_dev_rp10,
            MAX(std_dev) FILTER (WHERE return_period =   20) AS depth_std_dev_rp20,
            MAX(std_dev) FILTER (WHERE return_period =   50) AS depth_std_dev_rp50,
            MAX(std_dev) FILTER (WHERE return_period =  100) AS depth_std_dev_rp100,
            MAX(std_dev) FILTER (WHERE return_period =  200) AS depth_std_dev_rp200,
            MAX(std_dev) FILTER (WHERE return_period =  500) AS depth_std_dev_rp500,
            MAX(std_dev) FILTER (WHERE return_period = 1000) AS depth_std_dev_rp1000,
            MAX(std_dev) FILTER (WHERE return_period = 2000) AS depth_std_dev_rp2000,

            MAX(velocity) FILTER (WHERE return_period =   10) AS velocity_rp10,
            MAX(velocity) FILTER (WHERE return_period =   20) AS velocity_rp20,
            MAX(velocity) FILTER (WHERE return_period =   50) AS velocity_rp50,
            MAX(velocity) FILTER (WHERE return_period =  100) AS velocity_rp100,
            MAX(velocity) FILTER (WHERE return_period =  200) AS velocity_rp200,
            MAX(velocity) FILTER (WHERE return_period =  500) AS velocity_rp500,
            MAX(velocity) FILTER (WHERE return_period = 1000) AS velocity_rp1000,
            MAX(velocity) FILTER (WHERE return_period = 2000) AS velocity_rp2000,

            MAX(duration) FILTER (WHERE return_period =   10) AS duration_rp10,
            MAX(duration) FILTER (WHERE return_period =   20) AS duration_rp20,
            MAX(duration) FILTER (WHERE return_period =   50) AS duration_rp50,
            MAX(duration) FILTER (WHERE return_period =  100) AS duration_rp100,
            MAX(duration) FILTER (WHERE return_period =  200) AS duration_rp200,
            MAX(duration) FILTER (WHERE return_period =  500) AS duration_rp500,
            MAX(duration) FILTER (WHERE return_period = 1000) AS duration_rp1000,
            MAX(duration) FILTER (WHERE return_period = 2000) AS duration_rp2000
        FROM hazard
        GROUP BY id
    ),

    losses_wide AS (
        SELECT
            id,
            MAX(loss_min)  FILTER (WHERE return_period =   10) AS loss_min_rp10,
            MAX(loss_min)  FILTER (WHERE return_period =   20) AS loss_min_rp20,
            MAX(loss_min)  FILTER (WHERE return_period =   50) AS loss_min_rp50,
            MAX(loss_min)  FILTER (WHERE return_period =  100) AS loss_min_rp100,
            MAX(loss_min)  FILTER (WHERE return_period =  200) AS loss_min_rp200,
            MAX(loss_min)  FILTER (WHERE return_period =  500) AS loss_min_rp500,
            MAX(loss_min)  FILTER (WHERE return_period = 1000) AS loss_min_rp1000,
            MAX(loss_min)  FILTER (WHERE return_period = 2000) AS loss_min_rp2000,

            MAX(loss_mean) FILTER (WHERE return_period =   10) AS loss_mean_rp10,
            MAX(loss_mean) FILTER (WHERE return_period =   20) AS loss_mean_rp20,
            MAX(loss_mean) FILTER (WHERE return_period =   50) AS loss_mean_rp50,
            MAX(loss_mean) FILTER (WHERE return_period =  100) AS loss_mean_rp100,
            MAX(loss_mean) FILTER (WHERE return_period =  200) AS loss_mean_rp200,
            MAX(loss_mean) FILTER (WHERE return_period =  500) AS loss_mean_rp500,
            MAX(loss_mean) FILTER (WHERE return_period = 1000) AS loss_mean_rp1000,
            MAX(loss_mean) FILTER (WHERE return_period = 2000) AS loss_mean_rp2000,

            MAX(loss_std)  FILTER (WHERE return_period =   10) AS loss_std_rp10,
            MAX(loss_std)  FILTER (WHERE return_period =   20) AS loss_std_rp20,
            MAX(loss_std)  FILTER (WHERE return_period =   50) AS loss_std_rp50,
            MAX(loss_std)  FILTER (WHERE return_period =  100) AS loss_std_rp100,
            MAX(loss_std)  FILTER (WHERE return_period =  200) AS loss_std_rp200,
            MAX(loss_std)  FILTER (WHERE return_period =  500) AS loss_std_rp500,
            MAX(loss_std)  FILTER (WHERE return_period = 1000) AS loss_std_rp1000,
            MAX(loss_std)  FILTER (WHERE return_period = 2000) AS loss_std_rp2000,

            MAX(loss_max)  FILTER (WHERE return_period =   10) AS loss_max_rp10,
            MAX(loss_max)  FILTER (WHERE return_period =   20) AS loss_max_rp20,
            MAX(loss_max)  FILTER (WHERE return_period =   50) AS loss_max_rp50,
            MAX(loss_max)  FILTER (WHERE return_period =  100) AS loss_max_rp100,
            MAX(loss_max)  FILTER (WHERE return_period =  200) AS loss_max_rp200,
            MAX(loss_max)  FILTER (WHERE return_period =  500) AS loss_max_rp500,
            MAX(loss_max)  FILTER (WHERE return_period = 1000) AS loss_max_rp1000,
            MAX(loss_max)  FILTER (WHERE return_period = 2000) AS loss_max_rp2000,

            MAX(loss_mode_clamped) FILTER (WHERE return_period =   10) AS loss_mode_clamped_rp10,
            MAX(loss_mode_clamped) FILTER (WHERE return_period =   20) AS loss_mode_clamped_rp20,
            MAX(loss_mode_clamped) FILTER (WHERE return_period =   50) AS loss_mode_clamped_rp50,
            MAX(loss_mode_clamped) FILTER (WHERE return_period =  100) AS loss_mode_clamped_rp100,
            MAX(loss_mode_clamped) FILTER (WHERE return_period =  200) AS loss_mode_clamped_rp200,
            MAX(loss_mode_clamped) FILTER (WHERE return_period =  500) AS loss_mode_clamped_rp500,
            MAX(loss_mode_clamped) FILTER (WHERE return_period = 1000) AS loss_mode_clamped_rp1000,
            MAX(loss_mode_clamped) FILTER (WHERE return_period = 2000) AS loss_mode_clamped_rp2000,

            MAX(loss_mean_adjusted) FILTER (WHERE return_period =   10) AS loss_mean_adjusted_rp10,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period =   20) AS loss_mean_adjusted_rp20,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period =   50) AS loss_mean_adjusted_rp50,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period =  100) AS loss_mean_adjusted_rp100,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period =  200) AS loss_mean_adjusted_rp200,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period =  500) AS loss_mean_adjusted_rp500,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period = 1000) AS loss_mean_adjusted_rp1000,
            MAX(loss_mean_adjusted) FILTER (WHERE return_period = 2000) AS loss_mean_adjusted_rp2000
        FROM losses
        GROUP BY id
    ),

    dfs_wide AS (
        SELECT
            building_id,
            MAX(damage_percent)      FILTER (WHERE return_period =   10) AS dmg_pct_rp10,
            MAX(damage_percent)      FILTER (WHERE return_period =   20) AS dmg_pct_rp20,
            MAX(damage_percent)      FILTER (WHERE return_period =   50) AS dmg_pct_rp50,
            MAX(damage_percent)      FILTER (WHERE return_period =  100) AS dmg_pct_rp100,
            MAX(damage_percent)      FILTER (WHERE return_period =  200) AS dmg_pct_rp200,
            MAX(damage_percent)      FILTER (WHERE return_period =  500) AS dmg_pct_rp500,
            MAX(damage_percent)      FILTER (WHERE return_period = 1000) AS dmg_pct_rp1000,
            MAX(damage_percent)      FILTER (WHERE return_period = 2000) AS dmg_pct_rp2000,

            MAX(d_min)               FILTER (WHERE return_period =   10) AS dmg_d_min_rp10,
            MAX(d_min)               FILTER (WHERE return_period =   20) AS dmg_d_min_rp20,
            MAX(d_min)               FILTER (WHERE return_period =   50) AS dmg_d_min_rp50,
            MAX(d_min)               FILTER (WHERE return_period =  100) AS dmg_d_min_rp100,
            MAX(d_min)               FILTER (WHERE return_period =  200) AS dmg_d_min_rp200,
            MAX(d_min)               FILTER (WHERE return_period =  500) AS dmg_d_min_rp500,
            MAX(d_min)               FILTER (WHERE return_period = 1000) AS dmg_d_min_rp1000,
            MAX(d_min)               FILTER (WHERE return_period = 2000) AS dmg_d_min_rp2000,

            MAX(d_max)               FILTER (WHERE return_period =   10) AS dmg_d_max_rp10,
            MAX(d_max)               FILTER (WHERE return_period =   20) AS dmg_d_max_rp20,
            MAX(d_max)               FILTER (WHERE return_period =   50) AS dmg_d_max_rp50,
            MAX(d_max)               FILTER (WHERE return_period =  100) AS dmg_d_max_rp100,
            MAX(d_max)               FILTER (WHERE return_period =  200) AS dmg_d_max_rp200,
            MAX(d_max)               FILTER (WHERE return_period =  500) AS dmg_d_max_rp500,
            MAX(d_max)               FILTER (WHERE return_period = 1000) AS dmg_d_max_rp1000,
            MAX(d_max)               FILTER (WHERE return_period = 2000) AS dmg_d_max_rp2000,

            MAX(d_mode)              FILTER (WHERE return_period =   10) AS dmg_d_mode_rp10,
            MAX(d_mode)              FILTER (WHERE return_period =   20) AS dmg_d_mode_rp20,
            MAX(d_mode)              FILTER (WHERE return_period =   50) AS dmg_d_mode_rp50,
            MAX(d_mode)              FILTER (WHERE return_period =  100) AS dmg_d_mode_rp100,
            MAX(d_mode)              FILTER (WHERE return_period =  200) AS dmg_d_mode_rp200,
            MAX(d_mode)              FILTER (WHERE return_period =  500) AS dmg_d_mode_rp500,
            MAX(d_mode)              FILTER (WHERE return_period = 1000) AS dmg_d_mode_rp1000,
            MAX(d_mode)              FILTER (WHERE return_period = 2000) AS dmg_d_mode_rp2000,

            MAX(damage_percent_mean) FILTER (WHERE return_period =   10) AS dmg_pct_mean_rp10,
            MAX(damage_percent_mean) FILTER (WHERE return_period =   20) AS dmg_pct_mean_rp20,
            MAX(damage_percent_mean) FILTER (WHERE return_period =   50) AS dmg_pct_mean_rp50,
            MAX(damage_percent_mean) FILTER (WHERE return_period =  100) AS dmg_pct_mean_rp100,
            MAX(damage_percent_mean) FILTER (WHERE return_period =  200) AS dmg_pct_mean_rp200,
            MAX(damage_percent_mean) FILTER (WHERE return_period =  500) AS dmg_pct_mean_rp500,
            MAX(damage_percent_mean) FILTER (WHERE return_period = 1000) AS dmg_pct_mean_rp1000,
            MAX(damage_percent_mean) FILTER (WHERE return_period = 2000) AS dmg_pct_mean_rp2000,

            MAX(damage_percent_std)  FILTER (WHERE return_period =   10) AS dmg_pct_std_rp10,
            MAX(damage_percent_std)  FILTER (WHERE return_period =   20) AS dmg_pct_std_rp20,
            MAX(damage_percent_std)  FILTER (WHERE return_period =   50) AS dmg_pct_std_rp50,
            MAX(damage_percent_std)  FILTER (WHERE return_period =  100) AS dmg_pct_std_rp100,
            MAX(damage_percent_std)  FILTER (WHERE return_period =  200) AS dmg_pct_std_rp200,
            MAX(damage_percent_std)  FILTER (WHERE return_period =  500) AS dmg_pct_std_rp500,
            MAX(damage_percent_std)  FILTER (WHERE return_period = 1000) AS dmg_pct_std_rp1000,
            MAX(damage_percent_std)  FILTER (WHERE return_period = 2000) AS dmg_pct_std_rp2000,

            MAX(triangular_std_dev)  FILTER (WHERE return_period =   10) AS dmg_tri_std_rp10,
            MAX(triangular_std_dev)  FILTER (WHERE return_period =   20) AS dmg_tri_std_rp20,
            MAX(triangular_std_dev)  FILTER (WHERE return_period =   50) AS dmg_tri_std_rp50,
            MAX(triangular_std_dev)  FILTER (WHERE return_period =  100) AS dmg_tri_std_rp100,
            MAX(triangular_std_dev)  FILTER (WHERE return_period =  200) AS dmg_tri_std_rp200,
            MAX(triangular_std_dev)  FILTER (WHERE return_period =  500) AS dmg_tri_std_rp500,
            MAX(triangular_std_dev)  FILTER (WHERE return_period = 1000) AS dmg_tri_std_rp1000,
            MAX(triangular_std_dev)  FILTER (WHERE return_period = 2000) AS dmg_tri_std_rp2000,

            MAX(range_std_dev)       FILTER (WHERE return_period =   10) AS dmg_range_std_rp10,
            MAX(range_std_dev)       FILTER (WHERE return_period =   20) AS dmg_range_std_rp20,
            MAX(range_std_dev)       FILTER (WHERE return_period =   50) AS dmg_range_std_rp50,
            MAX(range_std_dev)       FILTER (WHERE return_period =  100) AS dmg_range_std_rp100,
            MAX(range_std_dev)       FILTER (WHERE return_period =  200) AS dmg_range_std_rp200,
            MAX(range_std_dev)       FILTER (WHERE return_period =  500) AS dmg_range_std_rp500,
            MAX(range_std_dev)       FILTER (WHERE return_period = 1000) AS dmg_range_std_rp1000,
            MAX(range_std_dev)       FILTER (WHERE return_period = 2000) AS dmg_range_std_rp2000
        FROM damage_function_statistics
        GROUP BY building_id
    ),

    struct_ddf AS (
        SELECT
            building_id,
            FIRST(damage_function_id ORDER BY weight DESC) AS struct_ddf_id,
            FIRST(first_floor_height  ORDER BY weight DESC) AS struct_ffh,
            FIRST(ffh_sig              ORDER BY weight DESC) AS struct_ffh_sig,
            FIRST(weight              ORDER BY weight DESC) AS struct_ddf_weight
        FROM structure_damage_functions
        GROUP BY building_id
    ),

    content_ddf AS (
        SELECT
            building_id,
            MAX(damage_function_id) AS content_ddf_id,
            MAX(weight)             AS content_ddf_weight
        FROM content_damage_functions
        GROUP BY building_id
    ),

    inventory_ddf AS (
        SELECT
            building_id,
            MAX(damage_function_id) AS inventory_ddf_id,
            MAX(weight)             AS inventory_ddf_weight
        FROM inventory_damage_functions
        GROUP BY building_id
    )

    SELECT
        b.id, b.bid, b.cbfips, b.st_damcat, b.occupancy_type, b.general_building_type,
        b.number_stories, b.area, b.first_floor_height, b.med_yr_blt, b.building_cost,
        b.content_cost, b.val_vehic, b.ftprntid, b.ftprntsrc, b.source, b.students,
        b.pop2amu65, b.pop2amo65, b.pop2pmu65, b.pop2pmo65, b.o65disable, b.u65disable,
        b.x, b.y, b.firmzone, b.grnd_elv_m, b.ground_elv, b.foundation_type, b.flood_peril_type,

        sd.struct_ddf_id, sd.struct_ffh, sd.struct_ffh_sig, sd.struct_ddf_weight,
        cd.content_ddf_id, cd.content_ddf_weight, id_.inventory_ddf_id, id_.inventory_ddf_weight,

        hw.depth_rp10, hw.depth_rp20, hw.depth_rp50, hw.depth_rp100, hw.depth_rp200, hw.depth_rp500, hw.depth_rp1000, hw.depth_rp2000,
        hw.depth_std_dev_rp10, hw.depth_std_dev_rp20, hw.depth_std_dev_rp50, hw.depth_std_dev_rp100, hw.depth_std_dev_rp200, hw.depth_std_dev_rp500, hw.depth_std_dev_rp1000, hw.depth_std_dev_rp2000,
        hw.velocity_rp10, hw.velocity_rp20, hw.velocity_rp50, hw.velocity_rp100, hw.velocity_rp200, hw.velocity_rp500, hw.velocity_rp1000, hw.velocity_rp2000,
        hw.duration_rp10, hw.duration_rp20, hw.duration_rp50, hw.duration_rp100, hw.duration_rp200, hw.duration_rp500, hw.duration_rp1000, hw.duration_rp2000,

        dfs.dmg_pct_rp10, dfs.dmg_pct_rp20, dfs.dmg_pct_rp50, dfs.dmg_pct_rp100, dfs.dmg_pct_rp200, dfs.dmg_pct_rp500, dfs.dmg_pct_rp1000, dfs.dmg_pct_rp2000,
        dfs.dmg_d_min_rp10, dfs.dmg_d_min_rp20, dfs.dmg_d_min_rp50, dfs.dmg_d_min_rp100, dfs.dmg_d_min_rp200, dfs.dmg_d_min_rp500, dfs.dmg_d_min_rp1000, dfs.dmg_d_min_rp2000,
        dfs.dmg_d_max_rp10, dfs.dmg_d_max_rp20, dfs.dmg_d_max_rp50, dfs.dmg_d_max_rp100, dfs.dmg_d_max_rp200, dfs.dmg_d_max_rp500, dfs.dmg_d_max_rp1000, dfs.dmg_d_max_rp2000,
        dfs.dmg_d_mode_rp10, dfs.dmg_d_mode_rp20, dfs.dmg_d_mode_rp50, dfs.dmg_d_mode_rp100, dfs.dmg_d_mode_rp200, dfs.dmg_d_mode_rp500, dfs.dmg_d_mode_rp1000, dfs.dmg_d_mode_rp2000,
        dfs.dmg_pct_mean_rp10, dfs.dmg_pct_mean_rp20, dfs.dmg_pct_mean_rp50, dfs.dmg_pct_mean_rp100, dfs.dmg_pct_mean_rp200, dfs.dmg_pct_mean_rp500, dfs.dmg_pct_mean_rp1000, dfs.dmg_pct_mean_rp2000,
        dfs.dmg_pct_std_rp10, dfs.dmg_pct_std_rp20, dfs.dmg_pct_std_rp50, dfs.dmg_pct_std_rp100, dfs.dmg_pct_std_rp200, dfs.dmg_pct_std_rp500, dfs.dmg_pct_std_rp1000, dfs.dmg_pct_std_rp2000,
        dfs.dmg_tri_std_rp10, dfs.dmg_tri_std_rp20, dfs.dmg_tri_std_rp50, dfs.dmg_tri_std_rp100, dfs.dmg_tri_std_rp200, dfs.dmg_tri_std_rp500, dfs.dmg_tri_std_rp1000, dfs.dmg_tri_std_rp2000,
        dfs.dmg_range_std_rp10, dfs.dmg_range_std_rp20, dfs.dmg_range_std_rp50, dfs.dmg_range_std_rp100, dfs.dmg_range_std_rp200, dfs.dmg_range_std_rp500, dfs.dmg_range_std_rp1000, dfs.dmg_range_std_rp2000,

        lw.loss_min_rp10, lw.loss_min_rp20, lw.loss_min_rp50, lw.loss_min_rp100, lw.loss_min_rp200, lw.loss_min_rp500, lw.loss_min_rp1000, lw.loss_min_rp2000,
        lw.loss_mean_rp10, lw.loss_mean_rp20, lw.loss_mean_rp50, lw.loss_mean_rp100, lw.loss_mean_rp200, lw.loss_mean_rp500, lw.loss_mean_rp1000, lw.loss_mean_rp2000,
        lw.loss_std_rp10, lw.loss_std_rp20, lw.loss_std_rp50, lw.loss_std_rp100, lw.loss_std_rp200, lw.loss_std_rp500, lw.loss_std_rp1000, lw.loss_std_rp2000,
        lw.loss_max_rp10, lw.loss_max_rp20, lw.loss_max_rp50, lw.loss_max_rp100, lw.loss_max_rp200, lw.loss_max_rp500, lw.loss_max_rp1000, lw.loss_max_rp2000,
        lw.loss_mode_clamped_rp10, lw.loss_mode_clamped_rp20, lw.loss_mode_clamped_rp50, lw.loss_mode_clamped_rp100, lw.loss_mode_clamped_rp200, lw.loss_mode_clamped_rp500, lw.loss_mode_clamped_rp1000, lw.loss_mode_clamped_rp2000,
        lw.loss_mean_adjusted_rp10, lw.loss_mean_adjusted_rp20, lw.loss_mean_adjusted_rp50, lw.loss_mean_adjusted_rp100, lw.loss_mean_adjusted_rp200, lw.loss_mean_adjusted_rp500, lw.loss_mean_adjusted_rp1000, lw.loss_mean_adjusted_rp2000,

        al.aal_min, al.aal_mean, al.aal_std, al.aal_max,

        b.geometry

    FROM buildings b
    LEFT JOIN struct_ddf    sd  ON b.id = sd.building_id
    LEFT JOIN content_ddf   cd  ON b.id = cd.building_id
    LEFT JOIN inventory_ddf id_ ON b.id = id_.building_id
    LEFT JOIN hazard_wide   hw  ON b.id = hw.id
    LEFT JOIN dfs_wide      dfs ON b.id = dfs.building_id
    LEFT JOIN losses_wide   lw  ON b.id = lw.id
    LEFT JOIN aal_losses    al  ON b.id = al.id

    WHERE al.aal_mean > 0

)TO '{output_path}'
(FORMAT PARQUET, COMPRESSION ZSTD);
"""


def export_wide_parquet(conn: duckdb.DuckDBPyConnection, output_path: Path) -> None:
    print(f"Exporting wide-format results to {output_path} ...")
    sql = WIDE_SQL.format(output_path=str(output_path).replace("\\", "/"))
    conn.execute(sql)
    print(f"Done. Output: {output_path}")


def main():
    print("Loading NSI buildings ...")
    nsi_gdf = gpd.read_file(str(NSI_GPKG))
    buildings = NsiBuildings(nsi_gdf, overrides={"id": "fd_id"})

    print("Building raster collection ...")
    raster_collection = build_raster_collection()

    vulnerability = InlandFloodVulnerability(buildings=buildings)

    print("Running InlandFloodAnalysis ...")
    analysis = InlandFloodAnalysis(
        raster_collection=raster_collection,
        buildings=buildings,
        vulnerability=vulnerability,
        calculate_aal=True,
    )

    with analysis:
        analysis.calculate_losses()
        print("Analysis complete. Exporting wide results ...")
        export_wide_parquet(analysis.conn, OUTPUT_PARQUET)


if __name__ == "__main__":
    main()
