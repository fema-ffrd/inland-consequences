"""Vectorized DDF matching utilities

Provides a vectorized implementation of lookup_damage_function that
matches building attributes against the flattened lookup table
produced by `create_complete_lookup_table`.

The implementation avoids Python-level loops over buildings and uses
joined DataFrame operations and groupby logic to determine match
status and pick the first matching damage function per building.
"""
from typing import Tuple

import pandas as pd


def lookup_damage_function(buildings_df: pd.DataFrame, complete_lookup_table: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized lookup damage functions for buildings using the complete flattened lookup table.

    See the project for expected column names. This function returns the original
    buildings with the following additional columns:
      - FLSBT_Range
      - Damage_Function_ID
      - Story_Min
      - Story_Max
      - Match_Status (Matched | No_Match | Story_Out_Of_Range | SQFT_Out_Of_Range)

    The algorithm is:
      1. Normalize building attributes and add an original index.
      2. Left-merge buildings with the lookup table on exact keys
         (construction, occupancy, foundation, flood peril).
      3. Vectorized-filter merged rows by story and sqft ranges.
      4. For each building pick the first matching lookup row (if any).
      5. Determine a per-building match status for diagnostics.
    """

    if buildings_df is None or complete_lookup_table is None:
        raise ValueError("buildings_df and complete_lookup_table must be provided")

    buildings = buildings_df.copy()

    # Normalize building attributes into temporary columns used for merge
    buildings['_Construction_Type'] = buildings['S_GENERALBUILDINGTYPE'].astype(str).str.upper().str.strip()
    buildings['_Occupancy_Type'] = buildings['S_OCCTYPE'].astype(str).str.upper().str.strip()
    buildings['_stories'] = pd.to_numeric(buildings['S_NUMSTORY'], errors='coerce')
    buildings['_sqft'] = pd.to_numeric(buildings.get('S_SQFT', 0), errors='coerce').fillna(0)
    buildings['_Foundation_Type'] = buildings['Foundation_Type'].astype(str).str.upper().str.strip()
    buildings['_Flood_Peril_Type'] = buildings['Flood_Peril_Type'].astype(str).str.upper().str.strip()

    # Preserve original order
    buildings['_original_index'] = range(len(buildings))

    # Perform left merge on the exact equality keys
    merged = buildings.merge(
        complete_lookup_table,
        left_on=['_Construction_Type', '_Occupancy_Type', '_Foundation_Type', '_Flood_Peril_Type'],
        right_on=['Construction_Type', 'Occupancy_Type', 'Foundation_Type', 'Flood_Peril_Type'],
        how='left',
        suffixes=("", "_lookup")
    )

    # Ensure numeric types for lookup ranges
    for col in ['Story_Min', 'Story_Max', 'SQFT_Min', 'SQFT_Max']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')

    # Candidate rows exist where the merge brought lookup values (FLSBT_Range notna)
    merged['_has_candidate'] = merged['FLSBT_Range'].notna()

    # Story match
    merged['_story_ok'] = (merged['Story_Min'] <= merged['_stories']) & (merged['Story_Max'] >= merged['_stories'])
    merged['_story_ok'] = merged['_story_ok'].fillna(False)

    # SQFT match: if lookup has no min/max (NaN) treat as unbounded
    sqft_min_ok = merged['SQFT_Min'].isna() | (merged['_sqft'] >= merged['SQFT_Min'])
    sqft_max_ok = merged['SQFT_Max'].isna() | (merged['_sqft'] <= merged['SQFT_Max'])
    merged['_sqft_ok'] = (sqft_min_ok & sqft_max_ok).fillna(False)

    # Final match per merged row
    merged['_final_match'] = merged['_has_candidate'] & merged['_story_ok'] & merged['_sqft_ok']

    # Pick the first matching lookup row for each building (if any)
    matched_rows = (
        merged[merged['_final_match']]
        .sort_values(['_original_index'])
        .groupby('_original_index', as_index=False)
        .first()
    )

    # Determine per-building diagnostics
    grp = merged.groupby('_original_index')

    has_candidate = grp['_has_candidate'].any()
    has_story_ok = grp['_story_ok'].any()
    has_sqft_ok = grp['_sqft_ok'].any()
    has_final = grp['_final_match'].any()

    status = pd.Series(index=has_candidate.index, dtype=object)
    status[~has_candidate] = 'No_Match'
    status[has_candidate & ~has_story_ok] = 'Story_Out_Of_Range'
    # Candidate and story ok but no sqft ok => sqft out of range
    status[has_candidate & has_story_ok & ~has_sqft_ok] = 'SQFT_Out_Of_Range'
    status[has_final] = 'Matched'

    # Build result DataFrame by merging matched_rows information back onto buildings
    result_cols = ['_original_index', 'FLSBT_Range', 'Damage_Function_ID', 'Story_Min', 'Story_Max']
    if '_original_index' not in matched_rows.columns:
        # No matches at all
        matched_rows = pd.DataFrame(columns=result_cols)

    # Ensure matched_rows has the expected columns
    for c in result_cols:
        if c not in matched_rows.columns:
            matched_rows[c] = pd.NA

    final = buildings.merge(
        matched_rows[result_cols],
        on='_original_index',
        how='left'
    )

    # Attach Match_Status
    status_df = status.reset_index()
    status_df.columns = ['_original_index', 'Match_Status']

    final = final.merge(status_df, on='_original_index', how='left')

    # Clean up temporary columns leaving the requested output columns
    drop_cols = ['_Construction_Type', '_Occupancy_Type', '_stories', '_sqft',
                 '_Foundation_Type', '_Flood_Peril_Type', '_original_index']
    for c in drop_cols:
        if c in final.columns:
            final = final.drop(columns=[c])

    # Reorder columns: original columns first then added ones
    added = ['FLSBT_Range', 'Damage_Function_ID', 'Story_Min', 'Story_Max', 'Match_Status']
    # Some buildings may not have had any lookup columns in merged (all NaN) -> ensure columns exist
    for c in added:
        if c not in final.columns:
            final[c] = pd.NA

    # Keep original order of columns + added at end
    original_cols = [c for c in buildings_df.columns]
    final = final[original_cols + added]

    return final


def _smoke_test() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return a tiny buildings and lookup table pair for quick manual testing."""
    lookup = pd.DataFrame([
        dict(Construction_Type='W', Occupancy_Type='RES1', Story_Min=1, Story_Max=1, SQFT_Min=pd.NA, SQFT_Max=pd.NA, FLSBT_Range='WSF001', Foundation_Type='BASE', Flood_Peril_Type='RLS', Damage_Function_ID=100),
        dict(Construction_Type='W', Occupancy_Type='RES1', Story_Min=2, Story_Max=4, SQFT_Min=pd.NA, SQFT_Max=pd.NA, FLSBT_Range='WSF002-004', Foundation_Type='BASE', Flood_Peril_Type='RLS', Damage_Function_ID=101),
    ])

    buildings = pd.DataFrame([
        dict(S_GENERALBUILDINGTYPE='W', S_OCCTYPE='RES1', S_NUMSTORY=1, S_SQFT=1500, Foundation_Type='BASE', Flood_Peril_Type='RLS'),
        dict(S_GENERALBUILDINGTYPE='W', S_OCCTYPE='RES1', S_NUMSTORY=3, S_SQFT=2000, Foundation_Type='BASE', Flood_Peril_Type='RLS'),
        dict(S_GENERALBUILDINGTYPE='W', S_OCCTYPE='RES1', S_NUMSTORY=5, S_SQFT=2000, Foundation_Type='BASE', Flood_Peril_Type='RLS'),
    ])

    return buildings, lookup


if __name__ == '__main__':
    b, l = _smoke_test()
    print('Buildings:')
    print(b)
    print('\nLookup:')
    print(l)
    print('\nResult:')
    print(lookup_damage_function(b, l))
