import pandas as pd
import duckdb
from pathlib import Path

# Mock data for buildings table (keeping this as mock for now)
# Updated to use values that match the real damage curves data

# testing the sql query - matches even with nulls (which are in most cases not permitted in real data)
# buildings_data = {
#     'point_id': [1, 2, 3, 4, 5],
#     'occupancy': ['RES1', 'RES1', 'COM1', 'RES1', 'COM1'],
#     'foundation': ['SLAB', 'CRAWL', None, 'BASE', 'SLAB'],
#     'stories': [1, 2, None, 1, 3],
#     'material': ['W', 'W', 'C', None, 'S']
# }

# simple example - gathers 7 dfs based on 7 flood perils and all else deterministic
buildings_data = {
    'point_id': [1],
    'occupancy': ['RES1'],
    'foundation': ['SLAB'],
    'stories': [1],
    'material': ['W'],
    'geom': ['POINT(-77.0 38.0)'],  # Mock geometry as WKT string
    'val_mean': [250000.0],  # Mean building value
    'val_std': [50000.0]  # Standard deviation of building value
}


buildings_df = pd.DataFrame(buildings_data)

# Load damage curves from actual data file
data_file = Path(__file__).parent.parent / 'src' / 'inland_consequences' / 'data' / 'df_lookup_structures.csv'
damage_curves_df = pd.read_csv(data_file)

# Rename columns to match the SQL query expectations
# The CSV has: construction_type, occupancy_type, story_min, story_max, foundation_type, damage_function_id
# We need: material, occupancy, stories, foundation, curve_id, plus ffh_mu and ffh_sig
damage_curves_df = damage_curves_df.rename(columns={
    'construction_type': 'material',
    'occupancy_type': 'occupancy',
    'foundation_type': 'foundation',
    'damage_function_id': 'curve_id'
})

# For stories, we'll use the story_min value as the primary story count
# In a real scenario, you might want to expand each row to cover the full range
damage_curves_df['stories'] = damage_curves_df['story_min']

# Add placeholder ffh_mu and ffh_sig (these would come from another source in reality)
# Using curve_id to generate semi-realistic values
damage_curves_df['ffh_mu'] = 1.0 # from building data
damage_curves_df['ffh_sig'] = 0.75 # static by foundation type

# Mock hazard_inputs data
hazard_data = {
    'point_id': [1],
    'return_periods': [[10, 25, 50, 100, 500]],
    'depth_means': [[1.5, 2.0, 2.5, 3.0, 4.0]],
    'depth_stds': [[0.3, 0.4, 0.5, 0.6, 0.8]]
}
hazard_df = pd.DataFrame(hazard_data)

# Create an in-memory DuckDB database and load the mock data
con = duckdb.connect(':memory:')
con.register('buildings', buildings_df)
con.register('damage_curves_long', damage_curves_df)
con.register('hazard_inputs', hazard_df)

print("Data loaded successfully!")
print("\nBuildings table:")
print(buildings_df)
print(f"\nDamage curves table: {len(damage_curves_df)} rows loaded from {data_file.name}")
print("Sample damage curves:")
print(damage_curves_df[['material', 'occupancy', 'foundation', 'stories', 'curve_id', 'ffh_mu', 'ffh_sig']].head(20))

sql_query = """
WITH 
curve_matches AS (
    SELECT 
        b.point_id,
        c.curve_id,
        c.ffh_mu,
        c.ffh_sig,
        -- NULL attributes match ANY value
        CASE 
            WHEN b.foundation IS NOT NULL AND c.foundation IS NOT NULL AND b.foundation != c.foundation THEN 0
            WHEN b.stories IS NOT NULL AND c.stories IS NOT NULL AND b.stories != c.stories THEN 0
            WHEN b.material IS NOT NULL AND c.material IS NOT NULL AND b.material != c.material THEN 0
            ELSE 1
        END AS is_match
    FROM buildings b
    CROSS JOIN (
        SELECT DISTINCT curve_id, occupancy, foundation, stories, material, ffh_mu, ffh_sig
        FROM damage_curves_long
    ) c
    WHERE b.occupancy = c.occupancy
),
filtered_matches AS (
    SELECT point_id, curve_id, ffh_mu, ffh_sig
    FROM curve_matches
    WHERE is_match = 1
),
curve_frequencies AS (
    SELECT 
        point_id, curve_id, ffh_mu, ffh_sig,
        COUNT(*) OVER (PARTITION BY point_id) AS total_matches,
        COUNT(*) OVER (PARTITION BY point_id, curve_id) AS curve_count
    FROM filtered_matches
),
unique_scenarios AS (
    SELECT DISTINCT
        point_id, curve_id, ffh_mu, ffh_sig,
        CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
    FROM curve_frequencies
)
SELECT 
    point_id,
    LIST({'curve_id': curve_id, 'weight': weight, 'ffh_mu': ffh_mu, 'ffh_sig': ffh_sig}) AS scenarios
FROM unique_scenarios
GROUP BY point_id;    
"""

# Explode ot computation grid (Create flat table with one row per (point, RP, scenario))
computation_grid_query = """
CREATE TABLE computation_grid AS
WITH hazard_expanded AS (
    SELECT 
        h.point_id,
        UNNEST(generate_series(1, len(h.return_periods))) AS rp_idx,
        UNNEST(h.return_periods) AS return_period,
        UNNEST(h.depth_means) AS flood_depth_mean,
        UNNEST(h.depth_stds) AS flood_depth_std
    FROM hazard_inputs h
),
scenarios_expanded AS (
    SELECT 
        bs.point_id,
        UNNEST(bs.scenarios) AS scenario
    FROM building_scenarios bs
)
SELECT 
    b.point_id,
    b.geom,
    b.val_mean,
    b.val_std,
    he.rp_idx,
    he.return_period,
    he.flood_depth_mean,
    he.flood_depth_std,
    se.scenario['curve_id'] AS curve_id,
    se.scenario['weight'] AS weight,
    se.scenario['ffh_mu'] AS ffh_mu,
    se.scenario['ffh_sig'] AS ffh_sig
FROM buildings b
JOIN hazard_expanded he ON b.point_id = he.point_id
JOIN scenarios_expanded se ON b.point_id = se.point_id
"""

# Query 3: Calculate structure depths with uncertainty
structure_depths_query = """
CREATE TABLE structure_depths AS
SELECT 
    *,
    -- Structure depth mean
    flood_depth_mean - ffh_mu AS struct_depth_mean,
    
    -- Structure depth uncertainty (Gaussian error propagation)
    -- σ²_struct = σ²_flood + σ²_ffh
    SQRT(POWER(flood_depth_std, 2) + POWER(ffh_sig, 2)) AS struct_depth_std,
    
    -- Bounds for damage lookup (99.7% confidence interval)
    GREATEST(0, flood_depth_mean - ffh_mu - 3*SQRT(POWER(flood_depth_std, 2) + POWER(ffh_sig, 2))) AS depth_lower,
    LEAST(19, flood_depth_mean - ffh_mu + 3*SQRT(POWER(flood_depth_std, 2) + POWER(ffh_sig, 2))) AS depth_upper
FROM computation_grid
"""

# Execute the query
print("\n" + "="*80)
print("Executing SQL query...")
print("="*80)

try:
    result = con.execute(sql_query).fetchdf()
    print("\nQuery 1 executed successfully!")
    print("\nResults:")
    print(result)
    
    # Show detailed breakdown for each point
    print("\n" + "="*80)
    print("Detailed breakdown by point_id:")
    print("="*80)
    for idx, row in result.iterrows():
        print(f"\nPoint ID: {row['point_id']}")
        print(f"Scenarios: {row['scenarios']}")
    
    # Register the result as 'building_scenarios' for the next query
    con.register('building_scenarios', result)
    
    con.execute(computation_grid_query)
    grid_result = con.execute("SELECT * FROM computation_grid").fetchdf()
    print("\nQuery 2 executed successfully!")
    print("\n" + "="*80)
    print("Computation Grid:")
    print("="*80)
    print(grid_result)
    
    con.execute(structure_depths_query)
    depths_result = con.execute("SELECT * FROM structure_depths").fetchdf()
    print("\nQuery 3 executed successfully!")
    print("\n" + "="*80)
    print("Structure Depths:")
    print("="*80)

    print(depths_result)
        
except Exception as e:
    print(f"\nError executing query: {e}")


con.close()