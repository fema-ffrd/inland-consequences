import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def __():
    # Setup cell - all imports needed by this notebook
    import marimo as mo
    import duckdb
    import pandas as pd
    import geopandas as gpd
    from pathlib import Path
    from typing import Optional, Tuple, List
    
    from sql_builder import (
        get_return_periods_from_db,
        build_export_wide_sql,
    )
    
    return (mo, duckdb, pd, gpd, Path, List, Optional, Tuple, 
            get_return_periods_from_db, build_export_wide_sql)



@app.function
def get_return_periods(db_path: str) -> list[int]:
    """
    Query the database to get actual return periods present.
    
    Args:
        db_path: Path to the duckdb database file
        
    Returns:
        List of return periods sorted in ascending order
    """
    import duckdb
    from sql_builder import get_return_periods_from_db
    
    return get_return_periods_from_db(db_path)


@app.function
def export_wide(
    db_path: str,
    output_path: str | None = None,
    output_format: str = "parquet",
    include_geometry: bool = True,
    compression: str = "zstd",
    geometry_table: str = "buildings",
    longitude_col: str = "x",
    latitude_col: str = "y"
) -> tuple:
    """
    Dynamically export results in wide format.
    
    This function discovers return periods and available columns in the database,
    then generates and executes the appropriate SQL query.

    One row per building, pivoted across all return periods.
    All hazard (depth, velocity, duration) and loss (min, mean, std, max) metrics
    are included as separate columns.
    
    Args:
        db_path: Path to the duckdb database
        output_path: Optional path to save results. If None, only returns dataframe.
        output_format: Output format - 'parquet', 'csv', 'geoparquet'
        include_geometry: Whether to include geometry column
        compression: Compression for parquet output ('zstd', 'snappy', etc.)
        geometry_table: Table name containing geometry/coordinate information (default: 'buildings')
        longitude_col: Column name for longitude in geometry_table (default: 'x')
        latitude_col: Column name for latitude in geometry_table (default: 'y')
        
    Returns:
        Tuple of (GeoDataFrame or DataFrame, path_or_status_string)
    """
    import duckdb
    import geopandas as gpd
    from pathlib import Path
    from sql_builder import build_export_wide_sql
    
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        # Build and execute the dynamic query
        sql = build_export_wide_sql(db_path, include_geometry=False)
        print("Executing export_wide query...")
        result_df = conn.execute(sql).df()
        print(f"Successfully exported {len(result_df)} buildings in wide format from database")
        
        # Join with geometry table if requested
        if include_geometry:
            # Find the common key column (usually 'id')
            key_col = 'id'
            if key_col not in result_df.columns:
                # Try to find the key column
                for col in result_df.columns:
                    if 'id' in col.lower() and col in ['id', 'bid', 'building_id']:
                        key_col = col
                        break
            
            print(f"Joining with {geometry_table} table on column '{key_col}'...")
            
            # Get coordinates from geometry table
            geom_query = f"""
            SELECT DISTINCT 
                {key_col},
                {longitude_col},
                {latitude_col}
            FROM {geometry_table}
            """
            
            geom_df = conn.execute(geom_query).df()
            
            # Merge with results
            result_df = result_df.merge(geom_df, on=key_col, how='left')
            
            # Create GeoDataFrame from coordinates
            if longitude_col in result_df.columns and latitude_col in result_df.columns:
                print(f"Creating point geometries from {longitude_col}/{latitude_col} coordinates...")
                result_gdf = gpd.GeoDataFrame(
                    result_df,
                    geometry=gpd.points_from_xy(result_df[longitude_col], result_df[latitude_col]),
                    crs="EPSG:4326"
                )
            else:
                print(f"Warning: Could not find {longitude_col} and/or {latitude_col} columns in {geometry_table}")
                result_gdf = result_df
        else:
            result_gdf = result_df
        
        # Save if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_format.lower() in ['parquet', 'geoparquet']:
                result_gdf.to_parquet(output_path, compression=compression)
                print(f"Saved to {output_path}")
            elif output_format.lower() == 'csv':
                df_for_csv = result_gdf.drop(columns=['geometry'], errors='ignore')
                df_for_csv.to_csv(output_path, index=False)
                print(f"Saved to {output_path}")
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            return (result_gdf, str(output_path))
        else:
            return (result_gdf, "in-memory")
        
    finally:
        conn.close()


@app.function
def load_results_as_geo(
    db_path: str,
    return_period: int | None = None,
    filter_buildings: str | None = None
) -> object:
    """
    Load loss results as a GeoDataFrame, optionally filtered.
    
    Loads from losses table and joins with building attributes.
    Creates point geometries at building coordinates.
    
    Args:
        db_path: Path to duckdb database
        return_period: Optional specific return period to filter (if None, loads all)
        filter_buildings: Optional SQL WHERE clause to filter buildings
                         Example: "b.occupancy_type = 'RES1'"
        
    Returns:
        GeoDataFrame with point geometries at building locations
    """
    import duckdb
    import geopandas as gpd
    
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        where_clause = "WHERE 1=1"
        if return_period:
            where_clause += f" AND l.return_period = {return_period}"
        if filter_buildings:
            where_clause += f" AND {filter_buildings}"
        
        sql = f"""
        SELECT 
            b.id,
            b.bid,
            b.occupancy_type,
            b.building_cost,
            l.return_period,
            l.loss_min,
            l.loss_mean,
            l.loss_std,
            l.loss_max,
            b.x,
            b.y,
            ST_Point(b.x, b.y) as geometry
        FROM buildings b
        JOIN losses l ON b.id = l.id
        {where_clause}
        ORDER BY b.id, l.return_period
        """
        
        result_df = conn.execute(sql).df()
        
        gdf = gpd.GeoDataFrame(
            result_df,
            geometry='geometry',
            crs="EPSG:4326"
        )
        
        return gdf
    finally:
        conn.close()


@app.function
def get_database_summary(db_path: str) -> dict:
    """
    Get a summary of database contents for debugging and exploration.
    
    Args:
        db_path: Path to duckdb database
        
    Returns:
        Dictionary with:
        - tables: list of table names
        - {table_name}_count: row count for each table
        - return_periods: list of distinct return periods
    """
    import duckdb
    
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        summary = {}
        
        # Get tables
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()
        summary['tables'] = [t[0] for t in tables]
        
        # Count records per table
        for table in summary['tables']:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                summary[f'{table}_count'] = count
            except:
                summary[f'{table}_count'] = 'Error querying'
        
        # Get return periods
        try:
            rps = conn.execute(
                "SELECT DISTINCT return_period FROM losses ORDER BY return_period"
            ).fetchall()
            summary['return_periods'] = [int(r[0]) for r in rps]
        except:
            summary['return_periods'] = 'Error querying losses table'
        
        return summary
    finally:
        conn.close()


@app.cell
def _(mo):
    mo.md(r"""
    # Inland Consequences Analysis Utilities
    
    This notebook provides shared utilities for the Inland Consequences analysis pipeline,
    dynamically adapting to the actual database schema.
    
    ## Key Functions (Importable with `@app.function`)
    
    These functions can be imported into other notebooks:
    
    - **export_wide()** - Pivot results into wide format (one row per building, one column per metric per return period)
    - **get_return_periods()** - Discover return periods in your database
    - **load_results_as_geo()** - Load results as a GeoDataFrame for GIS workflows
    - **get_database_summary()** - Inspect database contents
    
    ### Example Usage
    
    ```python
    from utils import export_wide, get_return_periods
    
    # Discover return periods
    rps = get_return_periods(db_path)
    
    # Export to wide format
    result_gdf, path = export_wide(db_path, output_path="results.parquet")
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Interactive Exploration
    
    Use the form below to explore your database.
    """)
    return


@app.cell
def _(mo):
    db_path_input = mo.ui.text(
        label="Database path:",
        placeholder="e.g., /path/to/inland_flood_analysis_*.duckdb"
    )
    return (db_path_input,)


@app.cell
def _(mo, db_path_input, get_database_summary):
    if db_path_input.value:
        try:
            summary = get_database_summary(db_path_input.value)
            mo.md(f"""
            ### Database Summary
            
            **Tables:** {', '.join(summary['tables'])}
            
            **Return Periods:** {summary.get('return_periods', 'Unknown')}
            
            **Record Counts:**
            - Buildings: {summary.get('buildings_count', '?')}
            - Losses: {summary.get('losses_count', '?')}
            - Hazard: {summary.get('hazard_count', '?')}
            - Damage Functions: {summary.get('damage_function_statistics_count', '?')}
            """)
        except Exception as e:
            mo.md(f"❌ Error: {e}")
    else:
        mo.md("📝 Enter a database path above to see summary")
    return


@app.cell
def _(mo):
    mo.md(r"""
    ---
    
    **Architecture:**
    - Functions use `@app.function` decorator for importability
    - Setup cell contains all shared imports
    - `sql_builder.py` handles dynamic SQL generation
    - `sql_templates/` contains reference documentation
    """)
    return


if __name__ == "__main__":
    app.run()