"""
SQL Builder for Inland Consequences Analysis

This module provides functions to dynamically build SQL queries for exporting
analysis results. Uses Jinja2 templating to adapt to actual database schemas.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import duckdb
from jinja2 import Template


def get_return_periods_from_db(db_path: str) -> List[int]:
    """
    Query database to discover available return periods.
    
    Args:
        db_path: Path to duckdb database
        
    Returns:
        List of return periods sorted in ascending order
    """
    conn = duckdb.connect(db_path, read_only=True)
    try:
        # Try losses table first (most reliable for analysis results)
        try:
            result = conn.execute(
                "SELECT DISTINCT return_period FROM losses ORDER BY return_period"
            ).fetchall()
            if result:
                return sorted([int(r[0]) for r in result])
        except Exception:
            pass
        
        # Fall back to hazard table
        result = conn.execute(
            "SELECT DISTINCT return_period FROM hazard ORDER BY return_period"
        ).fetchall()
        return sorted([int(r[0]) for r in result])
    finally:
        conn.close()


def get_available_columns(db_path: str, table_name: str) -> List[str]:
    """
    Get list of actual columns in a table.
    
    Args:
        db_path: Path to duckdb database
        table_name: Name of table to inspect
        
    Returns:
        List of column names
    """
    conn = duckdb.connect(db_path, read_only=True)
    try:
        result = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [row[1] for row in result]
    finally:
        conn.close()


def has_data_in_column(db_path: str, table_name: str, column_name: str) -> bool:
    """
    Check if a column has any non-NULL values.
    
    Args:
        db_path: Path to duckdb database
        table_name: Table to check
        column_name: Column to check
        
    Returns:
        True if column has data, False otherwise
    """
    conn = duckdb.connect(db_path, read_only=True)
    try:
        result = conn.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NOT NULL"
        ).fetchone()[0]
        return result > 0
    except Exception:
        return False
    finally:
        conn.close()


def build_hazard_pivot_cte(rps: List[int], db_path: str) -> Tuple[str, bool]:
    """
    Build Common Table Expression for pivoting hazard data.
    
    Args:
        rps: List of return periods
        db_path: Path to database (to check for optional columns)
        
    Returns:
        Tuple of (SQL string, bool indicating if hazard CTE was created)
    """
    # Check if hazard table has data
    conn = duckdb.connect(db_path, read_only=True)
    try:
        count = conn.execute("SELECT COUNT(*) FROM hazard").fetchone()[0]
        if count == 0:
            return ("", False)
    finally:
        conn.close()
    
    # Build pivot for depth (always present)
    cte = "hazard_wide AS (\n"
    cte += "    SELECT\n"
    cte += "        id,\n"
    
    depth_lines = []
    for rp in rps:
        depth_lines.append(f"        MAX(depth) FILTER (WHERE return_period = {rp}) AS depth_rp{rp}")
    cte += ",\n".join(depth_lines)
    
    # Add velocity if it has data
    if has_data_in_column(db_path, "hazard", "velocity"):
        cte += ",\n"
        velocity_lines = []
        for rp in rps:
            velocity_lines.append(f"        MAX(velocity) FILTER (WHERE return_period = {rp}) AS velocity_rp{rp}")
        cte += ",\n".join(velocity_lines)
    
    # Add duration if it has data
    if has_data_in_column(db_path, "hazard", "duration"):
        cte += ",\n"
        duration_lines = []
        for rp in rps:
            duration_lines.append(f"        MAX(duration) FILTER (WHERE return_period = {rp}) AS duration_rp{rp}")
        cte += ",\n".join(duration_lines)
    
    cte += "\n    FROM hazard\n"
    cte += "    GROUP BY id\n"
    cte += "),\n"
    
    return (cte, True)


def build_losses_pivot_cte(rps: List[int]) -> str:
    """
    Build Common Table Expression for pivoting losses data.
    
    Args:
        rps: List of return periods
        
    Returns:
        SQL string for losses CTE
    """
    cte = "losses_wide AS (\n"
    cte += "    SELECT\n"
    cte += "        id,\n"
    
    loss_cols = ['loss_min', 'loss_mean', 'loss_std', 'loss_max']
    loss_lines = []
    
    for col in loss_cols:
        for rp in rps:
            loss_lines.append(f"        MAX({col}) FILTER (WHERE return_period = {rp}) AS {col}_rp{rp}")
    
    cte += ",\n".join(loss_lines)
    cte += "\n    FROM losses\n"
    cte += "    GROUP BY id\n"
    cte += ")\n"
    
    return cte


def build_select_columns(rps: List[int], db_path: str, include_geometry: bool = True) -> str:
    """
    Build the SELECT clause with available building attributes and all pivoted columns.
    
    Args:
        rps: List of return periods
        db_path: Path to database (to check available columns)
        include_geometry: Whether to include geometry column
        
    Returns:
        SQL SELECT and FROM clause
    """
    sql = "SELECT\n"
    sql += "    b.id,\n"
    
    # Get available building columns
    available_cols = get_available_columns(db_path, "buildings")
    
    # Key building attributes in order of preference
    pref_cols = [
        'bid', 'occupancy_type', 'general_building_type', 'number_stories',
        'area', 'first_floor_height', 'building_cost', 'foundation_type',
        'x', 'y', 'cbfips', 'st_damcat'
    ]
    
    # Add up to 7 available preference columns
    added = 0
    for col in pref_cols:
        if col in available_cols and added < 7:
            sql += f"    b.{col},\n"
            added += 1
    
    # Add hazard columns if available
    if has_data_in_column(db_path, "hazard", "depth"):
        for rp in rps:
            sql += f"    hw.depth_rp{rp},\n"
        
        # Add velocity if present
        if has_data_in_column(db_path, "hazard", "velocity"):
            for rp in rps:
                sql += f"    hw.velocity_rp{rp},\n"
    
    # Add loss columns
    loss_cols = ['loss_min', 'loss_mean', 'loss_std', 'loss_max']
    for col in loss_cols:
        for rp in rps:
            sql += f"    lw.{col}_rp{rp},\n"
    
    # Add geometry if requested
    if include_geometry:
        sql += "    b.geometry\n"
    else:
        # Remove trailing comma from last line
        sql = sql.rstrip(',\n') + "\n"
    
    # Add FROM clause
    sql += "FROM buildings b\n"
    if has_data_in_column(db_path, "hazard", "depth"):
        sql += "LEFT JOIN hazard_wide hw ON b.id = hw.id\n"
    sql += "LEFT JOIN losses_wide lw ON b.id = lw.id\n"
    
    return sql


def build_export_wide_sql(
    db_path: str,
    include_geometry: bool = True
) -> str:
    """
    Build complete SQL query for wide-format export.
    
    Dynamically discovers return periods and available columns,
    then constructs appropriate SQL with all CTEs and joins.
    
    Args:
        db_path: Path to duckdb database
        include_geometry: Whether to include geometry column
        
    Returns:
        Complete SQL query string ready to execute
    """
    # Discover return periods
    rps = get_return_periods_from_db(db_path)
    if not rps:
        raise ValueError("No return periods found in database")
    
    print(f"Building query for return periods: {rps}")
    
    # Build CTEs
    hazard_cte, has_hazard = build_hazard_pivot_cte(rps, db_path)
    losses_cte = build_losses_pivot_cte(rps)
    select_clause = build_select_columns(rps, db_path, include_geometry)
    
    # Assemble complete SQL
    sql = "WITH\n"
    if has_hazard:
        sql += hazard_cte
    sql += losses_cte + "\n"
    sql += select_clause
    
    return sql


def export_wide_to_file(
    db_path: str,
    output_path: str,
    output_format: str = "parquet",
    compression: str = "zstd"
) -> None:
    """
    Execute export_wide query and write results to file.
    
    Args:
        db_path: Path to input duckdb database
        output_path: Path to output file
        output_format: Format ('parquet', 'csv', 'geoparquet')
        compression: Compression algorithm for parquet
    """
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        # Build and execute query
        sql = build_export_wide_sql(db_path, include_geometry=True)
        print(f"Executing export_wide query...")
        result = conn.execute(sql)
        
        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format.lower() in ['parquet', 'geoparquet']:
            result.write_parquet(
                str(output_path),
                compression=compression
            )
        elif output_format.lower() == 'csv':
            # CSV doesn't support geometry, so we'd need to handle that
            # For now, just use DuckDB's native CSV export
            result.write_csv(str(output_path))
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        print(f"Successfully wrote {output_path}")
    finally:
        conn.close()
