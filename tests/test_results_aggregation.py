"""Tests for FloodResultsAggregator.

Each test sets up a minimal in-memory DuckDB database (buildings + losses +
aal_losses) and two small reference parquet files in a temporary directory,
then verifies that the aggregated output matches independently calculated
expected values.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from inland_consequences.results_aggregation import FloodResultsAggregator

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

# Two return periods so the dynamic discovery logic is exercised.
RETURN_PERIODS = [100, 500]


def _write_parquet(path: Path, table: pa.Table) -> None:
    pq.write_table(table, str(path))


@pytest.fixture()
def xref_dir(tmp_path: Path) -> Path:
    """Write minimal community and watershed reference parquet files."""
    # community xref: two communities
    #   community_id=C1 <- block 150010001001001 (ratio 1.0)
    #   community_id=C2 <- block 150010001001002 (ratio 0.6)
    #   community_id=C3 <- block 150010001001002 (ratio 0.4)  (split block)
    community = pa.table(
        {
            "Area_ID": ["C1", "C2", "C3"],
            "CensusBlock": [
                "150010001001001",
                "150010001001002",
                "150010001001002",
            ],
            "Ratio": [1.0, 0.6, 0.4],
        }
    )
    _write_parquet(tmp_path / "hzCommunity_Block.parquet", community)

    # watershed xref
    watershed = pa.table(
        {
            "CensusBlock": ["150010001001001", "150010001001002"],
            "HUC": ["12030103", "12030104"],
        }
    )
    _write_parquet(tmp_path / "syWatershed_Block.parquet", watershed)

    return tmp_path


@pytest.fixture()
def in_memory_conn(xref_dir: Path) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB in-memory connection pre-loaded with test buildings, losses and AAL."""
    conn = duckdb.connect(":memory:")

    # buildings -----------------------------------------------------------
    # Building 1: state=15, county=15001, cbfips ends in 001 → community C1
    # Building 2: state=15, county=15001, cbfips ends in 002 → community C2(0.6) + C3(0.4)
    conn.execute("""
        CREATE TABLE buildings AS
        SELECT * FROM (VALUES
            (1, '150010001001001', 'RES', 'RES1', 'W', 'SLAB', NULL, 1.0, 1000.0,
             100000.0, 50000.0, NULL),
            (2, '150010001001002', 'COM', 'COM1', 'S', 'BASE', NULL, 2.0, 2000.0,
             200000.0, 100000.0, NULL)
        ) t(id, cbfips, st_damcat, occupancy_type, general_building_type,
            foundation_type, flood_peril_type, number_stories, area,
            building_cost, content_cost, geometry)
    """)

    # losses (long format) ------------------------------------------------
    # Building 1: RP100 loss_mean=5000, RP500 loss_mean=10000
    # Building 2: RP100 loss_mean=20000, RP500 loss_mean=40000
    conn.execute("""
        CREATE TABLE losses AS
        SELECT * FROM (VALUES
            (1, 100, 4500.0, 5000.0, 5000.0, 5000.0, 200.0, 5500.0),
            (1, 500, 9000.0, 10000.0, 10000.0, 10000.0, 400.0, 11000.0),
            (2, 100, 18000.0, 20000.0, 20000.0, 20000.0, 800.0, 22000.0),
            (2, 500, 36000.0, 40000.0, 40000.0, 40000.0, 1600.0, 44000.0)
        ) t(id, return_period, loss_min, loss_mean, loss_mean_adjusted,
            loss_mode_clamped, loss_std, loss_max)
    """)

    # aal_losses ----------------------------------------------------------
    # Building 1: baal_mean=200, Building 2: baal_mean=800
    conn.execute("""
        CREATE TABLE aal_losses AS
        SELECT * FROM (VALUES
            (1, 180.0, 200.0, 10.0, 220.0, 190.0, 210.0, 230.0),
            (2, 720.0, 800.0, 40.0, 880.0, 760.0, 840.0, 920.0)
        ) t(id, baal_min, baal_mean, baal_std, baal_max, taal_min, taal_mean, taal_max)
    """)

    yield conn
    conn.close()


@pytest.fixture()
def aggregator(
    in_memory_conn: duckdb.DuckDBPyConnection, xref_dir: Path
) -> FloodResultsAggregator:
    """Return an aggregator wired to the in-memory connection."""
    return FloodResultsAggregator(
        conn=in_memory_conn,
        community_xref_path=xref_dir / "hzCommunity_Block.parquet",
        watershed_xref_path=xref_dir / "syWatershed_Block.parquet",
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _row(df: pd.DataFrame, **kw) -> pd.Series:
    """Select a single row by matching column==value pairs."""
    mask = pd.Series([True] * len(df), index=df.index)
    for col, val in kw.items():
        mask &= df[col] == val
    rows = df[mask]
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}: {rows}"
    return rows.iloc[0]


# ---------------------------------------------------------------------------
# Dynamic return period discovery
# ---------------------------------------------------------------------------


def test_get_return_periods(aggregator: FloodResultsAggregator) -> None:
    assert aggregator.get_return_periods() == [100, 500]


# ---------------------------------------------------------------------------
# Census-hierarchy aggregation
# ---------------------------------------------------------------------------


class TestAggregateByState:
    def test_single_state_row(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert len(df) == 1

    def test_state_fips_derived_from_cbfips(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert df.iloc[0]["state_fips"] == "15"

    def test_building_count(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert df.iloc[0]["building_count"] == 2

    def test_total_exposure(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert df.iloc[0]["total_building_exposure"] == pytest.approx(300_000.0)
        assert df.iloc[0]["total_content_exposure"] == pytest.approx(150_000.0)
        assert df.iloc[0]["total_exposure"] == pytest.approx(450_000.0)

    def test_loss_columns_present(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert "loss_rp100" in df.columns
        assert "loss_rp500" in df.columns

    def test_loss_values(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        row = df.iloc[0]
        assert row["loss_rp100"] == pytest.approx(25_000.0)  # 5000 + 20000
        assert row["loss_rp500"] == pytest.approx(50_000.0)  # 10000 + 40000

    def test_loss_ratios(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        row = df.iloc[0]
        # loss_ratio = loss / building_exposure * 1_000_000
        expected_rp100 = round(25_000 / 300_000 * 1_000_000, 2)
        expected_rp500 = round(50_000 / 300_000 * 1_000_000, 2)
        assert row["loss_ratio_rp100"] == pytest.approx(expected_rp100)
        assert row["loss_ratio_rp500"] == pytest.approx(expected_rp500)

    def test_aal(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        row = df.iloc[0]
        assert row["aal_mean"] == pytest.approx(1000.0)  # 200 + 800
        expected_aal_ratio = round(1000 / 300_000 * 1_000_000, 2)
        assert row["aal_ratio"] == pytest.approx(expected_aal_ratio)

    def test_aal_min_max_columns_present(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        assert "aal_min" in df.columns
        assert "aal_max" in df.columns

    def test_aal_min_max_values(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state")
        row = df.iloc[0]
        assert row["aal_min"] == pytest.approx(180.0 + 720.0)   # 900.0
        assert row["aal_max"] == pytest.approx(220.0 + 880.0)   # 1100.0


class TestAggregateByCounty:
    def test_county_fips(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="county")
        assert len(df) == 1
        assert df.iloc[0]["county_fips"] == "15001"

    def test_building_count(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="county")
        assert df.iloc[0]["building_count"] == 2


class TestAggregateTractBlockGroupBlock:
    def test_tract(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="tract")
        assert len(df) == 1
        assert df.iloc[0]["tract_fips"] == "15001000100"

    def test_block_group(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="block_group")
        assert len(df) == 1
        assert df.iloc[0]["block_group_fips"] == "150010001001"

    def test_block(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="block")
        assert len(df) == 2
        fips = set(df["block_fips"])
        assert "150010001001001" in fips
        assert "150010001001002" in fips


# ---------------------------------------------------------------------------
# Community aggregation
# ---------------------------------------------------------------------------


class TestAggregateByCommmunity:
    def test_three_community_rows(self, aggregator: FloodResultsAggregator) -> None:
        # C1 (bldg1 fully), C2 (bldg2 × 0.6), C3 (bldg2 × 0.4)
        df = aggregator.aggregate(geography="community")
        assert len(df) == 3

    def test_community_c1_loss(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        row = _row(df, community_id="C1")
        assert row["loss_rp100"] == pytest.approx(5_000.0)

    def test_community_c2_loss_ratio_weighted(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        row = _row(df, community_id="C2")
        # 60% of bldg2's RP100 loss: 0.6 * 20000 = 12000
        assert row["loss_rp100"] == pytest.approx(12_000.0)

    def test_community_c3_loss_ratio_weighted(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        row = _row(df, community_id="C3")
        # 40% of bldg2's RP100 loss: 0.4 * 20000 = 8000
        assert row["loss_rp100"] == pytest.approx(8_000.0)

    def test_community_c1_aal(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        row = _row(df, community_id="C1")
        assert row["aal_mean"] == pytest.approx(200.0)

    def test_community_aal_min_max_columns_present(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        assert "aal_min" in df.columns
        assert "aal_max" in df.columns

    def test_community_c1_aal_min_max(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="community")
        row = _row(df, community_id="C1")
        # C1 = bldg1 fully (ratio 1.0): aal_min=180, aal_max=220
        assert row["aal_min"] == pytest.approx(180.0)
        assert row["aal_max"] == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# HUC aggregation
# ---------------------------------------------------------------------------


class TestAggregateByHuc:
    def test_two_huc8_rows(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=8)
        assert len(df) == 2

    def test_huc_id_values(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=8)
        assert set(df["huc"]) == {"12030103", "12030104"}

    def test_huc_loss(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=8)
        row = _row(df, huc="12030103")
        assert row["loss_rp100"] == pytest.approx(5_000.0)

    def test_huc_truncation_to_6_digits(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=6)
        # Both HUC-8 values begin with "120301", so they collapse into one row
        assert len(df) == 1
        assert df.iloc[0]["huc"] == "120301"

    def test_huc_aal_min_max_columns_present(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=8)
        assert "aal_min" in df.columns
        assert "aal_max" in df.columns

    def test_huc_aal_min_max_values(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="huc", huc_digits=8)
        row = _row(df, huc="12030103")
        # bldg1 maps to HUC 12030103: aal_min=180, aal_max=220
        assert row["aal_min"] == pytest.approx(180.0)
        assert row["aal_max"] == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# Attribute breakdowns
# ---------------------------------------------------------------------------


class TestAttributeBreakdown:
    def test_breakdown_by_st_damcat(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state", breakdown=["st_damcat"])
        # Two damage categories: RES (bldg1) and COM (bldg2)
        assert len(df) == 2
        res_row = _row(df, st_damcat="RES")
        assert res_row["building_count"] == 1
        assert res_row["loss_rp100"] == pytest.approx(5_000.0)

    def test_breakdown_by_occupancy_type(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="county", breakdown=["occupancy_type"])
        assert len(df) == 2
        com1_row = _row(df, occupancy_type="COM1")
        assert com1_row["loss_rp500"] == pytest.approx(40_000.0)

    def test_multi_breakdown(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(
            geography="state", breakdown=["st_damcat", "occupancy_type"]
        )
        assert len(df) == 2

    def test_invalid_breakdown_raises(self, aggregator: FloodResultsAggregator) -> None:
        with pytest.raises(ValueError, match="Unsupported breakdown field"):
            aggregator.aggregate(geography="state", breakdown=["nonexistent_field"])


# ---------------------------------------------------------------------------
# Alternative loss metrics
# ---------------------------------------------------------------------------


class TestLossMetrics:
    def test_loss_min_metric(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state", loss_metric="loss_min")
        row = df.iloc[0]
        # 4500 + 18000 = 22500
        assert row["loss_rp100"] == pytest.approx(22_500.0)

    def test_loss_max_metric(self, aggregator: FloodResultsAggregator) -> None:
        df = aggregator.aggregate(geography="state", loss_metric="loss_max")
        row = df.iloc[0]
        # 5500 + 22000 = 27500
        assert row["loss_rp100"] == pytest.approx(27_500.0)


# ---------------------------------------------------------------------------
# Context manager protocol
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager_with_db_path(self, xref_dir: Path, tmp_path: Path) -> None:
        """Aggregator opens and closes a .duckdb file when used as context manager."""
        db_path = tmp_path / "test.duckdb"
        # Create a minimal valid database
        with duckdb.connect(str(db_path)) as setup_conn:
            setup_conn.execute("""
                CREATE TABLE buildings AS
                SELECT 1 AS id, '150010001001001' AS cbfips, 'RES' AS st_damcat,
                       'RES1' AS occupancy_type, 'W' AS general_building_type,
                       'SLAB' AS foundation_type, NULL AS flood_peril_type,
                       1.0 AS number_stories, 1000.0 AS area,
                       100000.0 AS building_cost, 50000.0 AS content_cost,
                       NULL AS geometry
            """)
            setup_conn.execute("""
                CREATE TABLE losses AS
                SELECT 1 AS id, 100 AS return_period, 0.0 AS loss_min,
                       1000.0 AS loss_mean, 1000.0 AS loss_mean_adjusted,
                       1000.0 AS loss_mode_clamped, 50.0 AS loss_std, 1100.0 AS loss_max
            """)
            setup_conn.execute("""
                CREATE TABLE aal_losses AS
                SELECT 1 AS id, 45.0 AS baal_min, 50.0 AS baal_mean,
                       2.5 AS baal_std, 55.0 AS baal_max,
                       48.0 AS taal_min, 53.0 AS taal_mean, 58.0 AS taal_max
            """)

        with FloodResultsAggregator(
            db_path=db_path,
            community_xref_path=xref_dir / "hzCommunity_Block.parquet",
            watershed_xref_path=xref_dir / "syWatershed_Block.parquet",
        ) as agg:
            df = agg.aggregate(geography="state")
        assert len(df) == 1
        assert df.iloc[0]["state_fips"] == "15"

    def test_external_conn_not_closed(
        self, in_memory_conn: duckdb.DuckDBPyConnection, xref_dir: Path
    ) -> None:
        """When an external conn is provided, the aggregator should not close it."""
        agg = FloodResultsAggregator(
            conn=in_memory_conn,
            community_xref_path=xref_dir / "hzCommunity_Block.parquet",
            watershed_xref_path=xref_dir / "syWatershed_Block.parquet",
        )
        agg.__exit__(None, None, None)
        # Connection should still be usable
        result = in_memory_conn.execute("SELECT COUNT(*) FROM buildings").fetchone()
        assert result[0] == 2

    def test_cannot_provide_both_db_path_and_conn(
        self, in_memory_conn: duckdb.DuckDBPyConnection, xref_dir: Path, tmp_path: Path
    ) -> None:
        with pytest.raises(ValueError, match="not both"):
            FloodResultsAggregator(
                db_path=tmp_path / "x.duckdb",
                conn=in_memory_conn,
            )

    def test_must_provide_db_path_or_conn(self, xref_dir: Path) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            FloodResultsAggregator()
