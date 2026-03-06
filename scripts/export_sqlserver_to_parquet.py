"""
Export specified SQL Server tables to Parquet files using Windows (Integrated) Authentication.

Defaults target server: .\\HAZUSPLUSSRVR
Defaults database: syHazus
Default tables: syWatershed_Block,hzCommunity_Block
Default output dir: src/inland_consequences/data

Usage examples:
  python scripts\export_sqlserver_to_parquet.py
  python scripts\export_sqlserver_to_parquet.py --server ".\\HAZUSPLUSSRVR" --database syHazus \
      --tables syWatershed_Block,hzCommunity_Block --outdir src/inland_consequences/data

Requirements: pandas, pyodbc, pyarrow
Install with: pip install pandas pyodbc pyarrow
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List

try:
    import pandas as pd
except Exception as e:  # pragma: no cover - helpful error message
    print("Missing dependency 'pandas'. Install with: pip install pandas")
    raise

try:
    import pyodbc
except Exception as e:  # pragma: no cover
    print("Missing dependency 'pyodbc'. Install with: pip install pyodbc")
    raise


def make_connection(server: str, database: str, driver: str = "ODBC Driver 17 for SQL Server"):
    """Create a pyodbc connection using Windows Trusted Authentication."""
    conn_str = (
        rf"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


def export_table_to_parquet(conn, table: str, out_dir: str) -> str:
    """Read a full table into a DataFrame and write to Parquet. Returns written path."""
    out_path = os.path.join(out_dir, f"{table}.parquet")
    print(f"Reading table '{table}'...")
    # Simple full-table read; for very large tables you may want to implement chunked reads
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    print(f"Writing {len(df)} rows to {out_path}...")
    df.to_parquet(out_path, index=False)
    return out_path


def parse_tables(csv: str) -> List[str]:
    return [t.strip() for t in csv.split(",") if t.strip()]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export SQL Server tables to Parquet using Windows auth")
    parser.add_argument("--server", default=".\\HAZUSPLUSSRVR", help="SQL Server instance (default: .\\HAZUSPLUSSRVR)")
    parser.add_argument("--database", default="syHazus", help="Database name (default: syHazus)")
    parser.add_argument("--tables", default="syWatershed_Block,hzCommunity_Block", help="Comma-separated list of tables to export")
    parser.add_argument("--outdir", default=os.path.join("src", "inland_consequences", "data"), help="Output directory for Parquet files")
    parser.add_argument("--driver", default="ODBC Driver 17 for SQL Server", help="ODBC driver name to use")

    args = parser.parse_args(argv)

    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    tables = parse_tables(args.tables)
    if not tables:
        print("No tables specified; nothing to do.")
        return 0

    print(f"Connecting to server={args.server!r} database={args.database!r} using driver={args.driver!r}")
    try:
        conn = make_connection(args.server, args.database, args.driver)
    except Exception as exc:  # pragma: no cover - connection errors are environment-specific
        print("Failed to connect to SQL Server:", exc)
        # Helpful diagnostics to aid troubleshooting connection issues
        try:
            drivers = pyodbc.drivers()
            print("Available ODBC drivers:", drivers)
        except Exception:
            pass
        print("Suggestions:")
        print(" - Verify the SQL Server instance name and that the server is running (use SQL Server Configuration Manager or Services.msc).")
        print(" - Try alternate server names:")
        print("     '.' (local default instance)")
        print("     '.\\HAZUSPLUSSRVR' (local named instance)")
        print("     'localhost\\HAZUSPLUSSRVR'")
        print("     'tcp:servername,1433' (if your instance listens on a fixed TCP port)")
        print(" - Ensure the SQL Server Browser service is running for named instances.")
        print(" - If using Windows Authentication from a different machine, ensure your user has access and the network allows connections.")
        return 2

    try:
        for table in tables:
            try:
                path = export_table_to_parquet(conn, table, outdir)
                print(f"Exported: {path}")
            except Exception as e:  # table-specific failure shouldn't stop remaining exports
                print(f"Failed to export table {table}: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print("All done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
