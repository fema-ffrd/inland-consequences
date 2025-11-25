import pandas as pd
import geopandas as gpd
import pytest
import numpy as np

"""Processes defined in the scripts folder have been used to generate machine-readable lookup tables 
for damage functions based on Open-Hazus damage function tasks (a.k.a. Task4D). These tests validate
that the auto-generated (machine-readable) lookup tables produce the same results as the manually
validated lookup tables from Task4D documentation."""

@pytest.fixture
def sample_structures():
    """
    Randomly sampled data of potential structure types and flood perils from /data/df_lookup_structures.csv.
    Num_stories and sqft have been assigned real values (not ranges) to represent real structure attributes. 
    Add additional sample data if edge cases are discovered.

    NOTE: validated_damage_function_id column values have been manually validated against Task4D documentation
    """
    sample_data = [
        {
            'flood_specific_bldg_type': 'WMUH001-004', # reference only
            'construction_type': 'W',
            'occupancy_type': 'RES4',
            'num_stories': 2,
            'sqft': np.nan,
            'foundation_type': 'BASE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 669
        },
        {
            'flood_specific_bldg_type': 'WLRI001-006', # reference only
            'construction_type': 'W',
            'occupancy_type': 'IND5',
            'num_stories': 2,
            'sqft': np.nan,
            'foundation_type': 'BASE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 213
        },
        {
            'flood_specific_bldg_type': 'WLRI001-006', # reference only
            'construction_type': 'W',
            'occupancy_type': 'IND5',
            'num_stories': 2,
            'sqft': np.nan,
            'foundation_type': 'SLAB',
            'flood_peril_type': 'CMV',
            'validated_damage_function_id': 214
        },
        {
            'flood_specific_bldg_type': 'MECB001-004', # reference only
            'construction_type': 'M',
            'occupancy_type': 'EDU2',
            'num_stories': 4,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 213
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only
            'construction_type': 'M',
            'occupancy_type': 'EDU2',
            'num_stories': 5,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 218
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only
            'construction_type': 'M',
            'occupancy_type': 'IND5',
            'num_stories': 8,
            'sqft': np.nan,
            'foundation_type': 'SLAB',
            'flood_peril_type': 'RHS',
            'validated_damage_function_id': 218
        },
        {
            'flood_specific_bldg_type': 'SERB001', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 1,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 630
        },
        {
            'flood_specific_bldg_type': 'SERB002-004', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 2,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 634
        },
        {
            'flood_specific_bldg_type': 'SERB005-108', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 25,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLL',
            'validated_damage_function_id': 218
        },
        {
            'flood_specific_bldg_type': 'MECB001-004', # reference only
            'construction_type': 'M',
            'occupancy_type': 'EDU1',
            'num_stories': 3,
            'sqft': np.nan,
            'foundation_type': 'SHAL',
            'flood_peril_type': 'CHW',
            'validated_damage_function_id': 214
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only
            'construction_type': 'M',
            'occupancy_type': 'EDU1',
            'num_stories': 10,
            'sqft': np.nan,
            'foundation_type': 'SHAL',
            'flood_peril_type': 'CHW',
            'validated_damage_function_id': 219
        },
        {
            'flood_specific_bldg_type': 'MERB001', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3C',
            'num_stories': 1,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLS',
            'validated_damage_function_id': 597
        },
        {
            'flood_specific_bldg_type': 'MERB002-004', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3D',
            'num_stories': 4,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLS',
            'validated_damage_function_id': 601
        },
        {
            'flood_specific_bldg_type': 'MERB005-030', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3D',
            'num_stories': 30,
            'sqft': np.nan,
            'foundation_type': 'PILE',
            'flood_peril_type': 'RLS',
            'validated_damage_function_id': 218
        },
        {
            'flood_specific_bldg_type': 'MH', # reference only
            'construction_type': 'MH',
            'occupancy_type': 'RES2',
            'num_stories': 1,
            'sqft': np.nan,
            'foundation_type': 'SLAB',
            'flood_peril_type': 'RHS',
            'validated_damage_function_id': 699
        },
        {
            'flood_specific_bldg_type': 'MH', # reference only
            'construction_type': 'MH',
            'occupancy_type': 'RES2',
            'num_stories': 1,
            'sqft': np.nan,
            'foundation_type': 'SLAB',
            'flood_peril_type': 'CHW',
            'validated_damage_function_id': 680
        },
    ]
    
    return pd.DataFrame(sample_data)


def test_lookup_table_generation_structures(sample_structures):
    """Test that lookup table generation was performed correctly using sampled data and validated outputs"""
    
    # load the production-ready structure lookup table
    df_lookup_structures = pd.read_csv('src/inland_consequences/data/df_lookup_structures.csv')

    # use the sample data and production-ready lookup table to assign damage function IDs
    for idx, row in sample_structures.iterrows():
        mask = (
            (df_lookup_structures['construction_type'] == row['construction_type']) &
            (df_lookup_structures['occupancy_type'] == row['occupancy_type']) &
            (df_lookup_structures['story_min'] <= row['num_stories']) &
            (df_lookup_structures['story_max'] >= row['num_stories']) &
            ((df_lookup_structures['sqft_min'].isna()) | (df_lookup_structures['sqft_min'] <= row['sqft'])) &
            ((df_lookup_structures['sqft_max'].isna()) | (df_lookup_structures['sqft_max'] >= row['sqft'])) &
            (df_lookup_structures['foundation_type'] == row['foundation_type']) &
            (df_lookup_structures['flood_peril_type'] == row['flood_peril_type'])
        )
        matched_row = df_lookup_structures[mask]
        if not matched_row.empty:
            sample_structures.at[idx, 'damage_function_id'] = matched_row['damage_function_id'].values[0]
        else:
            sample_structures.at[idx, 'damage_function_id'] = np.nan

    # validate the assigned damage function IDs
    assigned_ids = sample_structures['damage_function_id'].tolist()
    assert assigned_ids == sample_structures['validated_damage_function_id'].tolist()
        
