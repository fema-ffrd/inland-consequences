"""Flood loss results aggregation.

Provides :class:`FloodResultsAggregator`, a standalone helper that reads a
DuckDB database produced by :class:`~inland_consequences.InlandFloodAnalysis`
and aggregates the site-specific building-level results to:

* **Geographic hierarchies** derived from the 15-digit Census Block FIPS
  (``cbfips``) stored on each building: state, county, census tract, census
  block group, census block, NFIP community, and HUC watershed.
* **Attribute breakdowns** across occupancy type, damage category,
  construction type, foundation type and flood peril type.

Return periods are discovered dynamically from the ``losses`` table so the
aggregator works regardless of the set of return periods used in the analysis.

Example usage::

    from inland_consequences.results_aggregation import FloodResultsAggregator

    with FloodResultsAggregator("analysis.duckdb") as agg:
        # Losses by county
        county_df = agg.aggregate(geography="county")

        # Losses by county broken down by occupancy type
        county_occ_df = agg.aggregate(
            geography="county",
            breakdown=["occupancy_type"],
        )

        # Losses by NFIP community
        community_df = agg.aggregate(geography="community")

        # Losses by HUC-8 watershed
        huc_df = agg.aggregate(geography="huc", huc_digits=8)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bundled reference data locations
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_COMMUNITY_XREF = _DATA_DIR / "hzCommunity_Block.parquet"
_DEFAULT_WATERSHED_XREF = _DATA_DIR / "syWatershed_Block.parquet"

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

GeographyLevel = Literal[
    "state",
    "county",
    "tract",
    "block_group",
    "block",
    "community",
    "huc",
]

LossMetric = Literal[
    "loss_mean",
    "loss_mean_adjusted",
    "loss_min",
    "loss_max",
    "loss_mode_clamped",
]

# ---------------------------------------------------------------------------
# FloodResultsAggregator
# ---------------------------------------------------------------------------


class FloodResultsAggregator:
    """Aggregate building-level flood loss results to geographic and attribute summaries.

    Parameters
    ----------
    db_path:
        Path to a DuckDB database produced by ``InlandFloodAnalysis``.  Mutually
        exclusive with *conn*.
    conn:
        An already-open ``duckdb.DuckDBPyConnection``.  Use this when calling
        from within an ``InlandFloodAnalysis`` context manager so that the same
        connection (and its in-memory tables) is reused.  Mutually exclusive with
        *db_path*.
    community_xref_path:
        Path to the census-block → NFIP-community mapping parquet
        (``hzCommunity_Block.parquet``).  Defaults to the bundled copy shipped
        with the package.
    watershed_xref_path:
        Path to the census-block → HUC mapping parquet
        (``syWatershed_Block.parquet``).  Defaults to the bundled copy shipped
        with the package.
    """

    # Number of cbfips prefix digits for each geographic level
    _GEO_FIPS_LEN: dict[str, int] = {
        "state": 2,
        "county": 5,
        "tract": 11,
        "block_group": 12,
        "block": 15,
    }

    # Column names for the geographic identifier
    _GEO_ID_COL: dict[str, str] = {
        "state": "state_fips",
        "county": "county_fips",
        "tract": "tract_fips",
        "block_group": "block_group_fips",
        "block": "block_fips",
        "community": "community_id",
        "huc": "huc",
    }

    # Permitted attribute breakdown fields
    BREAKDOWN_FIELDS: frozenset[str] = frozenset(
        {
            "st_damcat",
            "occupancy_type",
            "general_building_type",
            "foundation_type",
            "flood_peril_type",
        }
    )

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        conn: Optional[duckdb.DuckDBPyConnection] = None,
        community_xref_path: Optional[str | Path] = None,
        watershed_xref_path: Optional[str | Path] = None,
    ) -> None:
        if db_path is not None and conn is not None:
            raise ValueError("Provide either db_path or conn, not both.")
        if db_path is None and conn is None:
            raise ValueError("Provide either db_path or conn.")

        self._db_path = Path(db_path) if db_path is not None else None
        self._external_conn = conn
        self._owned_conn: Optional[duckdb.DuckDBPyConnection] = None

        self._community_xref = Path(
            community_xref_path if community_xref_path is not None else _DEFAULT_COMMUNITY_XREF
        )
        self._watershed_xref = Path(
            watershed_xref_path if watershed_xref_path is not None else _DEFAULT_WATERSHED_XREF
        )

        self._return_periods: Optional[list[int]] = None  # cached after first query

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "FloodResultsAggregator":
        if self._external_conn is not None:
            # Use the caller's connection; don't open or close it ourselves.
            return self
        if self._db_path is None:
            raise RuntimeError("Cannot open connection: db_path is not set.")
        self._owned_conn = duckdb.connect(str(self._db_path), read_only=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owned_conn is not None:
            self._owned_conn.close()
            self._owned_conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _conn(self) -> duckdb.DuckDBPyConnection:
        """Return the active DuckDB connection, opening one if needed."""
        if self._external_conn is not None:
            return self._external_conn
        if self._owned_conn is not None:
            return self._owned_conn
        # Fallback: open a read-only connection for single-shot calls.
        if self._db_path is None:
            raise RuntimeError("No connection available.")
        self._owned_conn = duckdb.connect(str(self._db_path), read_only=True)
        return self._owned_conn

    def get_return_periods(self) -> list[int]:
        """Return the sorted list of return periods present in the ``losses`` table."""
        if self._return_periods is None:
            rows = self._conn.execute(
                "SELECT DISTINCT return_period FROM losses ORDER BY return_period"
            ).fetchall()
            self._return_periods = [int(r[0]) for r in rows]
        return self._return_periods

    def _register_xrefs(self) -> None:
        """No-op: xref parquets are inlined directly in SQL via read_parquet()."""

    @property
    def _community_xref_sql(self) -> str:
        """SQL fragment for the community xref, usable inline in any query."""
        return (
            f"(SELECT Area_ID AS community_id, CensusBlock AS cbfips, Ratio AS ratio"
            f" FROM read_parquet('{self._community_xref.as_posix()}'))"
        )

    @property
    def _watershed_xref_sql(self) -> str:
        """SQL fragment for the watershed xref, usable inline in any query."""
        return (
            f"(SELECT CensusBlock AS cbfips, HUC AS huc"
            f" FROM read_parquet('{self._watershed_xref.as_posix()}'))"
        )

    def _build_loss_pivot_sql(self, loss_metric: str, table_alias: str = "l") -> str:
        """Build the SQL expression list that pivots long-format losses to wide columns."""
        rps = self.get_return_periods()
        cols = []
        for rp in rps:
            cols.append(
                f"    SUM({table_alias}.{loss_metric}) FILTER (WHERE {table_alias}.return_period = {rp}) AS loss_rp{rp}"
            )
        return ",\n".join(cols)

    def _build_loss_ratio_sql(self, rps: list[int]) -> str:
        """Build loss ratio expressions referencing pre-aggregated CTE columns."""
        cols = []
        for rp in rps:
            cols.append(
                f"    ROUND(la.loss_rp{rp} / NULLIF(bs.total_building_exposure, 0) * 1000000.0, 2)"
                f" AS loss_ratio_rp{rp}"
            )
        return ",\n".join(cols)

    def _build_aal_ratio_sql(self) -> str:
        return (
            "    ROUND(aa.aal_mean / NULLIF(bs.total_building_exposure, 0) * 1000000.0, 2)"
            " AS aal_ratio"
        )

    def _fips_agg_sql(
        self,
        geo_id_expr: str,
        geo_id_col: str,
        breakdown: list[str],
        loss_metric: str,
    ) -> str:
        """Build a complete aggregation SQL query using three-CTE pattern.

        Separates building exposure aggregation (building_stats), loss pivoting
        (loss_agg), and AAL aggregation (aal_agg) to avoid fan-out when the
        losses table has multiple rows per building.
        """
        rps = self.get_return_periods()

        breakdown_select = "".join(f",\n        b.{f}" for f in breakdown)
        breakdown_group = "".join(f", b.{f}" for f in breakdown)
        breakdown_select_outer = "".join(f",\n    bs.{f}" for f in breakdown)

        loss_cols = ",\n".join(
            f"        SUM(l.{loss_metric}) FILTER (WHERE l.return_period = {rp}) AS loss_rp{rp}"
            for rp in rps
        )
        loss_col_selects = ",\n".join(f"    la.loss_rp{rp}" for rp in rps)
        ratio_selects = self._build_loss_ratio_sql(rps)

        return f"""
        WITH building_stats AS (
            SELECT
                {geo_id_expr} AS {geo_id_col}{breakdown_select},
                COUNT(*) AS building_count,
                SUM(b.building_cost) AS total_building_exposure,
                SUM(COALESCE(b.content_cost, 0)) AS total_content_exposure,
                SUM(COALESCE(b.building_cost, 0) + COALESCE(b.content_cost, 0)) AS total_exposure
            FROM buildings b
            GROUP BY {geo_id_expr}{breakdown_group}
        ),
        loss_agg AS (
            SELECT
                {geo_id_expr} AS {geo_id_col}{breakdown_select},
                {loss_cols}
            FROM buildings b
            LEFT JOIN losses l ON b.id = l.id
            GROUP BY {geo_id_expr}{breakdown_group}
        ),
        aal_agg AS (
            SELECT
                {geo_id_expr} AS {geo_id_col}{breakdown_select},
                SUM(a.aal_min) AS aal_min,
                SUM(a.aal_mean) AS aal_mean,
                SUM(a.aal_max) AS aal_max
            FROM buildings b
            LEFT JOIN aal_losses a ON b.id = a.id
            GROUP BY {geo_id_expr}{breakdown_group}
        )
        SELECT
            bs.{geo_id_col}{breakdown_select_outer},
            bs.building_count,
            bs.total_building_exposure,
            bs.total_content_exposure,
            bs.total_exposure,
            {loss_col_selects},
            {ratio_selects},
            aa.aal_min,
            aa.aal_mean,
            aa.aal_max,
            {self._build_aal_ratio_sql()}
        FROM building_stats bs
        LEFT JOIN loss_agg la ON bs.{geo_id_col} = la.{geo_id_col}{self._join_breakdown_clause('bs', 'la', breakdown)}
        LEFT JOIN aal_agg aa ON bs.{geo_id_col} = aa.{geo_id_col}{self._join_breakdown_clause('bs', 'aa', breakdown)}
        ORDER BY bs.{geo_id_col}{', ' + ', '.join(f'bs.{f}' for f in breakdown) if breakdown else ''}
        """

    def _join_breakdown_clause(self, left: str, right: str, breakdown: list[str]) -> str:
        """Generate AND clauses for breakdown fields in a JOIN condition."""
        if not breakdown:
            return ""
        clauses = " AND ".join(
            f"({left}.{f} = {right}.{f} OR ({left}.{f} IS NULL AND {right}.{f} IS NULL))"
            for f in breakdown
        )
        return f" AND {clauses}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate(
        self,
        geography: GeographyLevel,
        breakdown: Optional[list[str]] = None,
        huc_digits: int = 8,
        loss_metric: LossMetric = "loss_mean",
    ) -> pd.DataFrame:
        """Aggregate results to the requested geographic and/or attribute level.

        Parameters
        ----------
        geography:
            The geographic aggregation level.  Census-hierarchy levels
            (``state``, ``county``, ``tract``, ``block_group``, ``block``) are
            derived from the 15-digit ``cbfips`` field on each building.
            ``community`` and ``huc`` use the bundled reference parquet files.
        breakdown:
            Optional list of building attribute columns to add as additional
            group-by dimensions.  Supported values: ``st_damcat``,
            ``occupancy_type``, ``general_building_type``, ``foundation_type``,
            ``flood_peril_type``.
        huc_digits:
            Number of HUC digits to use when ``geography="huc"``.  The bundled
            reference contains HUC-8 identifiers; pass a smaller even number
            (e.g. 6 or 4) to roll up to a coarser watershed unit.
        loss_metric:
            Which column from the ``losses`` table to aggregate.  Defaults to
            ``loss_mean``.

        Returns
        -------
        pandas.DataFrame
            One row per unique combination of geographic ID and breakdown
            dimensions.  Columns include ``building_count``,
            ``total_building_exposure``, ``total_content_exposure``,
            ``total_exposure``, ``loss_rp{N}`` and ``loss_ratio_rp{N}`` for
            each return period, ``aal_mean``, and ``aal_ratio``.
        """
        breakdown = list(breakdown or [])
        invalid = set(breakdown) - self.BREAKDOWN_FIELDS
        if invalid:
            raise ValueError(
                f"Unsupported breakdown field(s): {invalid}. "
                f"Allowed: {self.BREAKDOWN_FIELDS}"
            )

        self._register_xrefs()
        geo_id_col = self._GEO_ID_COL[geography]

        if geography in self._GEO_FIPS_LEN:
            return self._aggregate_fips(geography, geo_id_col, breakdown, loss_metric)
        elif geography == "community":
            return self._aggregate_community(geo_id_col, breakdown, loss_metric)
        elif geography == "huc":
            return self._aggregate_huc(geo_id_col, huc_digits, breakdown, loss_metric)
        else:
            raise ValueError(f"Unknown geography level: {geography!r}")

    # ------------------------------------------------------------------
    # Geographic aggregation implementations
    # ------------------------------------------------------------------

    def _aggregate_fips(
        self,
        geography: str,
        geo_id_col: str,
        breakdown: list[str],
        loss_metric: str,
    ) -> pd.DataFrame:
        """Aggregate using a LEFT(cbfips, N) prefix for Census hierarchy levels."""
        n = self._GEO_FIPS_LEN[geography]
        geo_id_expr = f"LEFT(b.cbfips, {n})"
        sql = self._fips_agg_sql(geo_id_expr, geo_id_col, breakdown, loss_metric)
        return self._conn.execute(sql).df()

    def _aggregate_community(
        self,
        geo_id_col: str,
        breakdown: list[str],
        loss_metric: str,
    ) -> pd.DataFrame:
        """Aggregate to NFIP community using the community xref with Ratio weighting.

        When a census block overlaps multiple communities the ``Ratio`` column
        allocates fractional shares of each building's losses to each community.
        """
        breakdown_select = "".join(f",\n    b.{f}" for f in breakdown)
        breakdown_group = "".join(f", b.{f}" for f in breakdown)

        rps = self.get_return_periods()
        loss_cols = ",\n".join(
            f"    SUM(cx.ratio * COALESCE("
            f"(SELECT {loss_metric} FROM losses WHERE id = b.id AND return_period = {rp})"
            f", 0)) AS loss_rp{rp}"
            for rp in rps
        )
        ratio_cols = ",\n".join(
            f"    ROUND(SUM(cx.ratio * COALESCE("
            f"(SELECT {loss_metric} FROM losses WHERE id = b.id AND return_period = {rp})"
            f", 0)) / NULLIF(SUM(cx.ratio * b.building_cost), 0) * 1000000.0, 2)"
            f" AS loss_ratio_rp{rp}"
            for rp in rps
        )

        sql = f"""
        WITH base AS (
            SELECT
                cx.community_id,
                cx.ratio{breakdown_select},
                b.id,
                b.building_cost,
                b.content_cost,
                a.aal_min,
                a.aal_mean,
                a.aal_max
            FROM buildings b
            JOIN {self._community_xref_sql} cx ON b.cbfips = cx.cbfips
            LEFT JOIN aal_losses a ON b.id = a.id
        ),
        losses_wide AS (
            SELECT
                l.id,
                {self._build_loss_pivot_sql(loss_metric).replace('b.', '')}
            FROM losses l
            GROUP BY l.id
        ),
        joined AS (
            SELECT
                base.community_id,
                base.ratio{breakdown_select.replace('b.', 'base.')},
                base.id,
                base.building_cost,
                base.content_cost,
                base.aal_min,
                base.aal_mean,
                base.aal_max,
                lw.*
            FROM base
            LEFT JOIN losses_wide lw ON base.id = lw.id
        )
        SELECT
            community_id{breakdown_group.replace('b.', '')},
            COUNT(DISTINCT id) AS building_count,
            SUM(ratio * building_cost) AS total_building_exposure,
            SUM(ratio * COALESCE(content_cost, 0)) AS total_content_exposure,
            SUM(ratio * (COALESCE(building_cost, 0) + COALESCE(content_cost, 0))) AS total_exposure,
            {self._build_community_loss_cols(rps)},
            {self._build_community_ratio_cols(rps)},
            SUM(ratio * COALESCE(aal_mean, 0)) AS aal_mean,
            SUM(ratio * COALESCE(aal_min, 0)) AS aal_min,
            SUM(ratio * COALESCE(aal_max, 0)) AS aal_max,
            ROUND(SUM(ratio * COALESCE(aal_mean, 0)) / NULLIF(SUM(ratio * building_cost), 0) * 1000000.0, 2) AS aal_ratio
        FROM joined
        GROUP BY community_id{breakdown_group.replace('b.', '')}
        ORDER BY community_id
        """
        return self._conn.execute(sql).df()

    def _build_community_loss_cols(self, rps: list[int]) -> str:
        return ",\n".join(
            f"            SUM(ratio * COALESCE(loss_rp{rp}, 0)) AS loss_rp{rp}"
            for rp in rps
        )

    def _build_community_ratio_cols(self, rps: list[int]) -> str:
        return ",\n".join(
            f"            ROUND(SUM(ratio * COALESCE(loss_rp{rp}, 0))"
            f" / NULLIF(SUM(ratio * building_cost), 0) * 1000000.0, 2) AS loss_ratio_rp{rp}"
            for rp in rps
        )

    def _aggregate_huc(
        self,
        geo_id_col: str,
        huc_digits: int,
        breakdown: list[str],
        loss_metric: str,
    ) -> pd.DataFrame:
        """Aggregate to HUC watershed using the watershed xref."""
        if huc_digits <= 0:
            raise ValueError("huc_digits must be a positive integer.")

        huc_expr = (
            f"LEFT(wx.huc, {huc_digits})" if huc_digits < 12 else "wx.huc"
        )

        breakdown_select = "".join(f",\n        b.{f}" for f in breakdown)
        breakdown_group = "".join(f", b.{f}" for f in breakdown)
        breakdown_select_outer = "".join(f",\n    bs.{f}" for f in breakdown)

        rps = self.get_return_periods()
        loss_cols = ",\n".join(
            f"        SUM(l.{loss_metric}) FILTER (WHERE l.return_period = {rp}) AS loss_rp{rp}"
            for rp in rps
        )
        loss_col_selects = ",\n".join(f"    la.loss_rp{rp}" for rp in rps)
        ratio_selects = self._build_loss_ratio_sql(rps)

        sql = f"""
        WITH building_stats AS (
            SELECT
                {huc_expr} AS {geo_id_col}{breakdown_select},
                COUNT(*) AS building_count,
                SUM(b.building_cost) AS total_building_exposure,
                SUM(COALESCE(b.content_cost, 0)) AS total_content_exposure,
                SUM(COALESCE(b.building_cost, 0) + COALESCE(b.content_cost, 0)) AS total_exposure
            FROM buildings b
            JOIN {self._watershed_xref_sql} wx ON b.cbfips = wx.cbfips
            GROUP BY {huc_expr}{breakdown_group}
        ),
        loss_agg AS (
            SELECT
                {huc_expr} AS {geo_id_col}{breakdown_select},
                {loss_cols}
            FROM buildings b
            JOIN {self._watershed_xref_sql} wx ON b.cbfips = wx.cbfips
            LEFT JOIN losses l ON b.id = l.id
            GROUP BY {huc_expr}{breakdown_group}
        ),
        aal_agg AS (
            SELECT
                {huc_expr} AS {geo_id_col}{breakdown_select},
                SUM(a.aal_min) AS aal_min,
                SUM(a.aal_mean) AS aal_mean,
                SUM(a.aal_max) AS aal_max
            FROM buildings b
            JOIN {self._watershed_xref_sql} wx ON b.cbfips = wx.cbfips
            LEFT JOIN aal_losses a ON b.id = a.id
            GROUP BY {huc_expr}{breakdown_group}
        )
        SELECT
            bs.{geo_id_col}{breakdown_select_outer},
            bs.building_count,
            bs.total_building_exposure,
            bs.total_content_exposure,
            bs.total_exposure,
            {loss_col_selects},
            {ratio_selects},
            aa.aal_min,
            aa.aal_mean,
            aa.aal_max,
            {self._build_aal_ratio_sql()}
        FROM building_stats bs
        LEFT JOIN loss_agg la ON bs.{geo_id_col} = la.{geo_id_col}{self._join_breakdown_clause('bs', 'la', breakdown)}
        LEFT JOIN aal_agg aa ON bs.{geo_id_col} = aa.{geo_id_col}{self._join_breakdown_clause('bs', 'aa', breakdown)}
        ORDER BY bs.{geo_id_col}{', ' + ', '.join(f'bs.{f}' for f in breakdown) if breakdown else ''}
        """
        return self._conn.execute(sql).df()
