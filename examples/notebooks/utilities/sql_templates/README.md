# SQL Templates

SQL templates for Inland Consequences analysis exports.

## Overview

These templates document the SQL structure used by `sql_builder.py`. The actual SQL generation is dynamic and adapts to available return periods and columns in the database.

## Files

- **export_wide_base.sql** - Reference template showing the structure of the wide-format export query

## How it works

The Python module `sql_builder.py` reads the database schema at runtime and constructs the complete SQL query by:

1. Discovering available return periods from the database
2. Checking which optional columns exist (velocity, duration, etc.)
3. Building CTEs (Common Table Expressions) for each data source
4. Constructing the final SELECT statement with dynamic column lists

This ensures the query always works with your actual data, regardless of which return periods or hazard components were included in the analysis.
