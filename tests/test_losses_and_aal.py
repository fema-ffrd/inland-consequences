"""Tests for _calculate_losses and _calculate_aal with known, verifiable math.

These tests bypass the full damage-function matching / interpolation pipeline
and inject known ``damage_function_statistics`` rows directly so every
intermediate and final value can be independently reproduced.

Test groups
-----------
1. **Losses & AAL — min / mean / max**
   Verifies that ``losses`` and ``aal_losses`` tables carry correct
   ``loss_min``, ``loss_mean``, ``loss_max`` and ``aal_min``, ``aal_mean``,
   ``aal_max`` derived from ``d_min``, ``damage_percent_mean``, and ``d_max``.

2. **Damage statistics — mean & std deviation**
   Verifies that ``damage_percent_mean`` (hinge-corrected) and
   ``damage_percent_std`` (half-range) are computed correctly from
   ``d_min``, ``d_mean``, ``d_max`` via the triangular distribution
   formulas used in ``_compute_damage_function_statistics``.
"""

import math
import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
from unittest.mock import MagicMock, patch

from inland_consequences.nsi_buildings import NsiBuildings
from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.raster_collection import RasterCollection
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction

# ---------------------------------------------------------------------------
# Constants — known inputs for hand-verifiable math
# ---------------------------------------------------------------------------
# Two buildings, two return periods, constant depths per building per RP.
#
# Building 1: cost = 100_000, depths: RP100 = 2.0 ft, RP500 = 4.0 ft
# Building 2: cost = 200_000, depths: RP100 = 3.0 ft, RP500 = 5.0 ft
#
# Uncertainty (std_dev) = 1.0 everywhere → min depth = depth-1, max depth = depth+1
#
BUILDING_COST_1 = 100_000.0
BUILDING_COST_2 = 200_000.0
STD_DEV = 1.0
DEPTHS = {
    100: [2.0, 3.0],
    500: [4.0, 5.0],
}

# We fabricate a perfectly linear DDF: damage% = depth * 5 (percentage points).
# This means at depth 2.0 ft → 10 (i.e. 10%), depth 4.0 ft → 20, etc.
# The DDF stores values as percentage points (0–100), not fractions.
# At 0.0 ft → 0, and our curve has points at 0, 2, 4, 6, 8, 10 ft.
# slope = 5 percentage-points per foot.
SLOPE = 5.0  # damage percentage points per foot


def _expected_damage(depth: float) -> float:
    """Expected damage percentage from a perfectly linear DDF with slope 5 pp/ft.

    Returns percentage points (0-100 scale), matching the DDF convention.
    """
    if depth <= 0.0:
        return 0.0
    return depth * SLOPE


# tmp_path is a built-in pytest fixture for temporary directories.
# To create the duckdb files in a known location use: uv run pytest --basetemp=outputs

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mock_buildings_for_losses():
    """Two-building NsiBuildings with known costs."""
    data = {
        "target_fid": [1, 2],
        "occtype": ["RES1", "RES1"],
        "bldgtype": ["W", "W"],
        "found_ht": [1.0, 1.0],
        "found_type": ["S", "S"],
        "num_story": [1, 1],
        "sqft": [1000, 1500],
        "val_struct": [BUILDING_COST_1, BUILDING_COST_2],
        "val_cont": [50_000.0, 60_000.0],
        "geometry": ["POINT (0 0)", "POINT (1 1)"],
    }
    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.GeoSeries.from_wkt(data["geometry"]),
        crs="EPSG:4326",
    )
    return NsiBuildings(gdf)


@pytest.fixture(scope="module")
def mock_rasters_constant():
    """RasterCollection mock returning constant depths with fixed uncertainty."""
    mock_collection = MagicMock(spec=RasterCollection)
    mock_collection.return_periods.return_value = [100, 500]

    def _sample_for_rp(rp, geometries):
        n = len(geometries)
        idx = pd.Index(range(n))
        depths = DEPTHS[rp][:n]
        return {
            "depth": pd.Series(depths, index=idx),
            "uncertainty": pd.Series([STD_DEV] * n, index=idx),
            "velocity": pd.Series([np.nan] * n, index=idx),
            "duration": pd.Series([np.nan] * n, index=idx),
        }

    mock_collection.sample_for_rp.side_effect = _sample_for_rp

    # Also wire up .get() for _calculate_exposure (not used in our path,
    # but keeps the mock complete)
    def _get(rp):
        depth_raster = MagicMock(spec=AbstractRasterReader)
        depth_raster.get_value_vectorized.return_value = DEPTHS[rp]
        return {
            "depth": depth_raster,
            "uncertainty": float(STD_DEV),
            "velocity": None,
            "duration": None,
        }

    mock_collection.get.side_effect = _get
    return mock_collection


@pytest.fixture(scope="module")
def mock_vulnerability_noop():
    """Vulnerability mock that does nothing (damage is computed via SQL)."""
    mock = MagicMock(spec=AbstractVulnerabilityFunction)
    return mock


# ---------------------------------------------------------------------------
# Synthetic linear DDF injection
# ---------------------------------------------------------------------------

def _inject_linear_ddf(self_obj, connection):
    """Replace real vulnerability CSVs with a single linear DDF curve.

    Creates lookup tables mapping RES1 → damage_function_id = 1, and a
    ``ddf_structure`` table with a perfectly linear curve:
    damage% = depth * 5 (percentage points per foot).
    """
    # xref_structures: one row matching RES1 + Slab + 1-story + Wood
    xref_struct = pd.DataFrame({
        "construction_type": pd.array(["W"], dtype="string"),
        "occupancy_type": pd.array(["RES1"], dtype="string"),
        "story_min": pd.array([1], dtype="Int32"),
        "story_max": pd.array([3], dtype="Int32"),
        "sqft_min": pd.array([pd.NA], dtype="Int32"),
        "sqft_max": pd.array([pd.NA], dtype="Int32"),
        "flsbt_range": pd.array([pd.NA], dtype="string"),
        "foundation_type": pd.array(["SLAB"], dtype="string"),
        "flood_peril_type": pd.array([pd.NA], dtype="string"),
        "damage_function_id": [1],
    })
    connection.execute("DROP TABLE IF EXISTS xref_structures")
    connection.execute(
        "CREATE TABLE xref_structures AS SELECT * FROM xref_struct"
    )

    # xref_contents: map RES1 → ddf 1
    xref_cont = pd.DataFrame({
        "construction_type": pd.array([pd.NA], dtype="string"),
        "occupancy_type": pd.array(["RES1"], dtype="string"),
        "story_min": pd.array([pd.NA], dtype="Int32"),
        "story_max": pd.array([pd.NA], dtype="Int32"),
        "sqft_min": pd.array([pd.NA], dtype="Int32"),
        "sqft_max": pd.array([pd.NA], dtype="Int32"),
        "flsbt_range": pd.array([pd.NA], dtype="string"),
        "foundation_type": pd.array([pd.NA], dtype="string"),
        "flood_peril_type": pd.array([pd.NA], dtype="string"),
        "damage_function_id": [1],
    })
    connection.execute("DROP TABLE IF EXISTS xref_contents")
    connection.execute(
        "CREATE TABLE xref_contents AS SELECT * FROM xref_cont"
    )

    # xref_inventory
    xref_inv = pd.DataFrame({
        "occupancy_type": pd.array(["RES1"], dtype="string"),
        "foundation_type": pd.array([pd.NA], dtype="string"),
        "flood_peril_type": pd.array([pd.NA], dtype="string"),
        "damage_function_id": [1],
    })
    connection.execute("DROP TABLE IF EXISTS xref_inventory")
    connection.execute(
        "CREATE TABLE xref_inventory AS SELECT * FROM xref_inv"
    )

    # ddf_structure: one linear curve — damage% = depth * 5 (i.e., 5% per foot)
    # Columns for depths: -4, -2, 0, 2, 4, 6, 8, 10
    # Values: 0, 0, 0, 10, 20, 30, 40, 50  (percentage points)
    ddf = pd.DataFrame({
        "ddf_id": [1],
        "comment": ["linear_test_curve"],
        "depth_m4_0": [0.0],
        "depth_m2_0": [0.0],
        "depth_0_0": [0.0],
        "depth_2_0": [10.0],
        "depth_4_0": [20.0],
        "depth_6_0": [30.0],
        "depth_8_0": [40.0],
        "depth_10_0": [50.0],
    })
    connection.execute("DROP TABLE IF EXISTS ddf_structure")
    connection.execute(
        "CREATE TABLE ddf_structure AS SELECT * FROM ddf"
    )


# ---------------------------------------------------------------------------
# Pipeline fixture — runs once per test class, persists to tmp_path duckdb
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def pipeline_results(
    mock_buildings_for_losses, mock_rasters_constant, mock_vulnerability_noop, tmp_path_factory
):
    """Run the full pipeline once per class with a tmp_path-based duckdb file.

    Patches ``_create_vulnerability_tables`` to inject the synthetic linear DDF
    and ``_get_db_identifier`` to persist the database in the pytest temp directory.
    """
    tmp_path = tmp_path_factory.mktemp("losses_aal")
    db_path = str(tmp_path / "test_losses.duckdb")

    with patch.object(
        InlandFloodAnalysis,
        "_create_vulnerability_tables",
        _inject_linear_ddf,
    ), patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=db_path,
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=mock_rasters_constant,
            buildings=mock_buildings_for_losses,
            vulnerability=mock_vulnerability_noop,
            calculate_aal=True,
        )
        with analysis:
            analysis.calculate_losses()
            yield analysis


# ---------------------------------------------------------------------------
# Helper — compute expected values using the same formulas as the SQL
# ---------------------------------------------------------------------------

def _expected_damage_stats(depth: float, std_dev: float):
    """Replicate the SQL triangular-distribution statistics for a depth."""
    d_mean = _expected_damage(depth)
    d_min = _expected_damage(depth - std_dev)
    d_max = _expected_damage(depth + std_dev)

    mode_raw = 3 * d_mean - d_min - d_max
    mode_clamped = max(d_min, min(d_max, mode_raw))

    # Hinge-corrected mean
    damage_percent_mean = d_mean + (d_min + d_max - 2 * d_mean) * (1.0 / math.sqrt(2 * math.pi))
    # Half-range std
    damage_percent_std = abs(d_max - d_min) / 2.0
    # Triangular std dev
    triangular_std_dev = math.sqrt(abs(
        (d_min**2 + d_max**2 + mode_clamped**2
         - d_min * d_max
         - d_min * mode_clamped
         - d_max * mode_clamped) / 18
    ))
    range_std_dev = (d_max - d_min) / 4.0 if (d_max - d_min) != 0 else None

    return {
        "d_mean": d_mean,
        "d_min": d_min,
        "d_max": d_max,
        "d_mode": mode_clamped,
        "damage_percent_mean": damage_percent_mean,
        "damage_percent_std": damage_percent_std,
        "triangular_std_dev": triangular_std_dev,
        "range_std_dev": range_std_dev,
    }


def _expected_aal(losses_100, losses_500):
    """Trapezoidal AAL between two return periods (100, 500).

    p_100 = 1/100 = 0.01
    p_500 = 1/500 = 0.002
    Sorted DESC by probability → p_start = 0.01, p_end = 0.002
    Width = 0.01 - 0.002 = 0.008
    AAL = ((loss_100 + loss_500) / 2) * 0.008
    """
    p_width = (1.0 / 100) - (1.0 / 500)  # 0.008
    return ((losses_100 + losses_500) / 2.0) * p_width


# ===================================================================
# Test Group 1: Losses & AAL — min, mean, max
# ===================================================================

class TestLossesMinMeanMax:
    """Verify loss_min, loss_mean, loss_max and aal_min, aal_mean, aal_max."""

    def test_losses_table_has_expected_rows(self, pipeline_results):
        """Each building × return period → one row in losses."""
        conn = pipeline_results.conn
        count = conn.execute("SELECT COUNT(*) FROM losses").fetchone()[0]
        # 2 buildings × 2 return periods = 4 rows
        assert count == 4

    # ---- loss_min ---------------------------------------------------

    def test_loss_min_building1_rp100(self, pipeline_results):
        conn = pipeline_results.conn
        depth_min = DEPTHS[100][0] - STD_DEV  # 2.0 - 1.0 = 1.0
        expected_d_min = _expected_damage(depth_min)  # 1.0 * 5 = 5.0 (percentage points)
        expected = BUILDING_COST_1 * expected_d_min / 100.0  # 100_000 * 5.0 = 500_000
        row = conn.execute(
            "SELECT loss_min FROM losses WHERE ID = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_loss_min_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        depth_min = DEPTHS[500][1] - STD_DEV  # 5.0 - 1.0 = 4.0
        expected_d_min = _expected_damage(depth_min)  # 4.0 * 5 = 20.0 (percentage points)
        expected = BUILDING_COST_2 * expected_d_min / 100.0  # 200_000 * 20.0 = 4_000_000
        row = conn.execute(
            "SELECT loss_min FROM losses WHERE ID = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    # ---- loss_max ---------------------------------------------------

    def test_loss_max_building1_rp100(self, pipeline_results):
        conn = pipeline_results.conn
        depth_max = DEPTHS[100][0] + STD_DEV  # 2.0 + 1.0 = 3.0
        expected_d_max = _expected_damage(depth_max)  # 3.0 * 5 = 15.0
        expected = BUILDING_COST_1 * expected_d_max / 100.0 # 100_000 * 15.0 = 1_500_000
        row = conn.execute(
            "SELECT loss_max FROM losses WHERE ID = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_loss_max_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        depth_max = DEPTHS[500][1] + STD_DEV  # 5.0 + 1.0 = 6.0
        expected_d_max = _expected_damage(depth_max)  # 6.0 * 5 = 30.0
        expected = BUILDING_COST_2 * expected_d_max / 100.0  # 200_000 * 30.0 = 6_000_000
        row = conn.execute(
            "SELECT loss_max FROM losses WHERE ID = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    # ---- loss_mean --------------------------------------------------

    def test_loss_mean_building1_rp100(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        expected = BUILDING_COST_1 * stats["damage_percent_mean"] / 100.0
        row = conn.execute(
            "SELECT loss_mean FROM losses WHERE ID = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_loss_mean_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        expected = BUILDING_COST_2 * stats["damage_percent_mean"] / 100.0
        row = conn.execute(
            "SELECT loss_mean FROM losses WHERE ID = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    # ---- loss_std ---------------------------------------------------

    def test_loss_std_building1_rp100(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        expected = BUILDING_COST_1 * stats["damage_percent_std"] / 100.0
        row = conn.execute(
            "SELECT loss_std FROM losses WHERE ID = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    # ---- AAL min / mean / max ---------------------------------------

    def test_aal_table_has_expected_rows(self, pipeline_results):
        """One AAL row per building."""
        conn = pipeline_results.conn
        count = conn.execute("SELECT COUNT(*) FROM aal_losses").fetchone()[0]
        assert count == 2

    def test_aal_min_building1(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][0], STD_DEV)
        loss_min_100 = BUILDING_COST_1 * stats_100["d_min"] / 100.0
        loss_min_500 = BUILDING_COST_1 * stats_500["d_min"] / 100.0
        expected = _expected_aal(loss_min_100, loss_min_500)
        row = conn.execute(
            "SELECT aal_min FROM aal_losses WHERE ID = 1"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_mean_building1(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][0], STD_DEV)
        loss_mean_100 = BUILDING_COST_1 * stats_100["damage_percent_mean"] / 100.0
        loss_mean_500 = BUILDING_COST_1 * stats_500["damage_percent_mean"] / 100.0
        expected = _expected_aal(loss_mean_100, loss_mean_500)
        row = conn.execute(
            "SELECT aal_mean FROM aal_losses WHERE ID = 1"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_max_building1(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][0], STD_DEV)
        loss_max_100 = BUILDING_COST_1 * stats_100["d_max"] / 100.0
        loss_max_500 = BUILDING_COST_1 * stats_500["d_max"] / 100.0
        expected = _expected_aal(loss_max_100, loss_max_500)
        row = conn.execute(
            "SELECT aal_max FROM aal_losses WHERE ID = 1"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_min_building2(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][1], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        loss_min_100 = BUILDING_COST_2 * stats_100["d_min"] / 100.0
        loss_min_500 = BUILDING_COST_2 * stats_500["d_min"] / 100.0
        expected = _expected_aal(loss_min_100, loss_min_500)
        row = conn.execute(
            "SELECT aal_min FROM aal_losses WHERE ID = 2"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_mean_building2(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][1], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        loss_mean_100 = BUILDING_COST_2 * stats_100["damage_percent_mean"] / 100.0
        loss_mean_500 = BUILDING_COST_2 * stats_500["damage_percent_mean"] / 100.0
        expected = _expected_aal(loss_mean_100, loss_mean_500)
        row = conn.execute(
            "SELECT aal_mean FROM aal_losses WHERE ID = 2"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_max_building2(self, pipeline_results):
        conn = pipeline_results.conn
        stats_100 = _expected_damage_stats(DEPTHS[100][1], STD_DEV)
        stats_500 = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        loss_max_100 = BUILDING_COST_2 * stats_100["d_max"] / 100.0
        loss_max_500 = BUILDING_COST_2 * stats_500["d_max"] / 100.0
        expected = _expected_aal(loss_max_100, loss_max_500)
        row = conn.execute(
            "SELECT aal_max FROM aal_losses WHERE ID = 2"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(expected, rel=1e-6)

    def test_aal_min_less_than_mean_less_than_max(self, pipeline_results):
        """AAL values should form a consistent ordering: min <= mean <= max."""
        conn = pipeline_results.conn
        rows = conn.execute(
            "SELECT ID, aal_min, aal_mean, aal_max FROM aal_losses ORDER BY ID"
        ).fetchall()
        for row in rows:
            bld_id, aal_min, aal_mean, aal_max = row
            assert aal_min <= aal_mean, f"Building {bld_id}: aal_min > aal_mean"
            assert aal_mean <= aal_max, f"Building {bld_id}: aal_mean > aal_max"

    def test_each_building_has_exactly_one_damage_function(self, pipeline_results):
        """Every building should have exactly one damage function assigned.

        With the injected xref_structures containing a single matching entry
        (W + RES1 + story_min=1 + story_max=3 + SLAB), each building should
        produce exactly one row in structure_damage_functions with weight=1.0.
        This guards against duplicate assignments that would distort loss calculations.
        """
        conn = pipeline_results.conn

        building_ids = conn.execute(
            "SELECT ID FROM buildings ORDER BY ID"
        ).fetchdf()

        counts = conn.execute("""
            SELECT building_id, COUNT(*) as func_count
            FROM structure_damage_functions
            GROUP BY building_id
            ORDER BY building_id
        """).fetchdf()

        # Every building must appear in structure_damage_functions
        assert len(counts) == len(building_ids), (
            f"Expected {len(building_ids)} buildings in structure_damage_functions, "
            f"got {len(counts)}"
        )

        # Each building must have exactly one damage function row
        for _, row in counts.iterrows():
            assert row['func_count'] == 1, (
                f"Building {int(row['building_id'])} has {int(row['func_count'])} damage "
                f"function(s) assigned; expected exactly 1"
            )


# ===================================================================
# Test Group 2: Damage statistics — mean & std deviation
# ===================================================================

class TestDamageStatistics:
    """Verify damage_percent_mean (hinge-corrected) and damage_percent_std
    (half-range) as well as triangular_std_dev and range_std_dev."""

    def test_damage_percent_mean_building1_rp100(self, pipeline_results):
        """Hinge-corrected mean should equal Python-computed value."""
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        row = conn.execute(
            "SELECT damage_percent_mean FROM damage_function_statistics "
            "WHERE building_id = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["damage_percent_mean"], rel=1e-6)

    def test_damage_percent_mean_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        row = conn.execute(
            "SELECT damage_percent_mean FROM damage_function_statistics "
            "WHERE building_id = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["damage_percent_mean"], rel=1e-6)

    def test_damage_percent_std_building1_rp100(self, pipeline_results):
        """damage_percent_std = |d_max - d_min| / 2."""
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        row = conn.execute(
            "SELECT damage_percent_std FROM damage_function_statistics "
            "WHERE building_id = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["damage_percent_std"], rel=1e-6)

    def test_damage_percent_std_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        row = conn.execute(
            "SELECT damage_percent_std FROM damage_function_statistics "
            "WHERE building_id = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["damage_percent_std"], rel=1e-6)

    def test_triangular_std_dev_building1_rp100(self, pipeline_results):
        """Triangular std dev from (d_min, d_max, mode_clamped)."""
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[100][0], STD_DEV)
        row = conn.execute(
            "SELECT triangular_std_dev FROM damage_function_statistics "
            "WHERE building_id = 1 AND return_period = 100"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["triangular_std_dev"], rel=1e-6)

    def test_triangular_std_dev_building2_rp500(self, pipeline_results):
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[500][1], STD_DEV)
        row = conn.execute(
            "SELECT triangular_std_dev FROM damage_function_statistics "
            "WHERE building_id = 2 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["triangular_std_dev"], rel=1e-6)

    def test_range_std_dev_building1_rp500(self, pipeline_results):
        """range_std_dev = (d_max - d_min) / 4."""
        conn = pipeline_results.conn
        stats = _expected_damage_stats(DEPTHS[500][0], STD_DEV)
        row = conn.execute(
            "SELECT range_std_dev FROM damage_function_statistics "
            "WHERE building_id = 1 AND return_period = 500"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(stats["range_std_dev"], rel=1e-6)

    def test_d_mode_clamped_within_range(self, pipeline_results):
        """d_mode must always be between d_min and d_max."""
        conn = pipeline_results.conn
        rows = conn.execute(
            "SELECT building_id, return_period, d_min, d_max, d_mode "
            "FROM damage_function_statistics"
        ).fetchall()
        for row in rows:
            bld_id, rp, d_min, d_max, d_mode = row
            assert d_min <= d_mode <= d_max, (
                f"Building {bld_id}, RP {rp}: d_mode={d_mode} "
                f"not in [{d_min}, {d_max}]"
            )

    @pytest.mark.parametrize(
        "building_idx,rp",
        [(0, 100), (0, 500), (1, 100), (1, 500)],
        ids=["bld1-rp100", "bld1-rp500", "bld2-rp100", "bld2-rp500"],
    )
    def test_d_min_d_mean_d_max_values(self, pipeline_results, building_idx, rp):
        """Verify d_min/d_mean/d_max match the expected interpolated damages."""
        conn = pipeline_results.conn
        depth = DEPTHS[rp][building_idx]
        bld_id = building_idx + 1

        exp_d_mean = _expected_damage(depth)
        exp_d_min = _expected_damage(depth - STD_DEV)
        exp_d_max = _expected_damage(depth + STD_DEV)

        row = conn.execute(
            "SELECT damage_percent, d_min, d_max FROM damage_function_statistics "
            "WHERE building_id = ? AND return_period = ?",
            [bld_id, rp],
        ).fetchone()
        assert row is not None
        actual_d_mean, actual_d_min, actual_d_max = row
        assert actual_d_mean == pytest.approx(exp_d_mean, rel=1e-6)
        assert actual_d_min == pytest.approx(exp_d_min, rel=1e-6)
        assert actual_d_max == pytest.approx(exp_d_max, rel=1e-6)
