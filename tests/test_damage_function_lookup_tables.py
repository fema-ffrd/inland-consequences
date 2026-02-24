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
    Randomly sampled data of potential structure types and flood perils from /data/df_lookup.csv.
    Num_stories and sqft have been assigned real values (not ranges) to represent real structure attributes. 
    Add additional sample data if edge cases are discovered.

    NOTE: validated_building_damage_function_id column values have been manually validated against Task4D documentation
    """
    sample_data = [
        {
            'flood_specific_bldg_type': 'WMUH001-004', # reference only (contents uses WMUH002-004)
            'construction_type': 'W',
            'occupancy_type': 'RES4',
            'num_stories': 2,
            'sqft': None,
            'foundation_type': 'BASE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 669,
            'validated_contents_damage_function_id': 400,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'WLRI001-006', # reference only
            'construction_type': 'W',
            'occupancy_type': 'IND5',
            'num_stories': 2,
            'sqft': None,
            'foundation_type': 'BASE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 213,
            'validated_contents_damage_function_id': 884,
            'validated_inventory_damage_function_id': 111
        },
        {
            'flood_specific_bldg_type': 'WLRI001-006', # reference only
            'construction_type': 'W',
            'occupancy_type': 'IND5',
            'num_stories': 2,
            'sqft': None,
            'foundation_type': 'SLAB',  # 4-letter code
            'flood_peril_type': 'CMV',
            'validated_building_damage_function_id': 214,
            'validated_contents_damage_function_id': 883,
            'validated_inventory_damage_function_id': 111
        },
        {
            'flood_specific_bldg_type': 'MECB001-004', # reference only (contents uses MECB001-030)
            'construction_type': 'M',
            'occupancy_type': 'EDU2',
            'num_stories': 4,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 213,
            'validated_contents_damage_function_id': 888,
            'validated_inventory_damage_function_id': None # undefined for educational
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only (contents uses MECB001-030)
            'construction_type': 'M',
            'occupancy_type': 'EDU2',
            'num_stories': 5,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 218,
            'validated_contents_damage_function_id': 888,
            'validated_inventory_damage_function_id': None # undefined for educational
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only (contents uses MECB001-030)
            'construction_type': 'M',
            'occupancy_type': 'IND5',
            'num_stories': 8,
            'sqft': None,
            'foundation_type': 'SLAB',  # 4-letter code
            'flood_peril_type': 'RHS',
            'validated_building_damage_function_id': 218,
            'validated_contents_damage_function_id': 883,
            'validated_inventory_damage_function_id': 111
        },
        {
            'flood_specific_bldg_type': 'SERB001', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 1,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 630,
            'validated_contents_damage_function_id': 421,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'SERB002-004', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 2,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 634,
            'validated_contents_damage_function_id': 422,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'SERB005-108', # reference only
            'construction_type': 'S',
            'occupancy_type': 'RES3C',
            'num_stories': 25,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLL',
            'validated_building_damage_function_id': 218,
            'validated_contents_damage_function_id': 406,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'MECB001-004', # reference only (contents uses MECB001-030)
            'construction_type': 'M',
            'occupancy_type': 'EDU1',
            'num_stories': 3,
            'sqft': None,
            'foundation_type': 'SHAL',  # 4-letter code
            'flood_peril_type': 'CHW',
            'validated_building_damage_function_id': 214,
            'validated_contents_damage_function_id': 887,
            'validated_inventory_damage_function_id': None # undefined for educational
        },
        {
            'flood_specific_bldg_type': 'MECB005-030', # reference only (contents uses MECB001-030)
            'construction_type': 'M',
            'occupancy_type': 'EDU1',
            'num_stories': 10,
            'sqft': None,
            'foundation_type': 'SHAL',  # 4-letter code
            'flood_peril_type': 'CHW',
            'validated_building_damage_function_id': 219,
            'validated_contents_damage_function_id': 887,
            'validated_inventory_damage_function_id': None # undefined for educational
        },
        {
            'flood_specific_bldg_type': 'MERB001', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3C',
            'num_stories': 1,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLS',
            'validated_building_damage_function_id': 597,
            'validated_contents_damage_function_id': 421,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'MERB002-004', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3D',
            'num_stories': 4,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLS',
            'validated_building_damage_function_id': 601,
            'validated_contents_damage_function_id': 422,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'MERB005-030', # reference only
            'construction_type': 'M',
            'occupancy_type': 'RES3D',
            'num_stories': 30,
            'sqft': None,
            'foundation_type': 'PILE',  # 4-letter code
            'flood_peril_type': 'RLS',
            'validated_building_damage_function_id': 218,
            'validated_contents_damage_function_id': 406,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'MH', # reference only
            'construction_type': 'MH',
            'occupancy_type': 'RES2',
            'num_stories': 1,
            'sqft': None,
            'foundation_type': 'SLAB',  # 4-letter code
            'flood_peril_type': 'RHS',
            'validated_building_damage_function_id': 699,
            'validated_contents_damage_function_id': 446,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
        {
            'flood_specific_bldg_type': 'MH', # reference only
            'construction_type': 'MH',
            'occupancy_type': 'RES2',
            'num_stories': 1,
            'sqft': None,
            'foundation_type': 'SLAB',  # 4-letter code
            'flood_peril_type': 'CHW',
            'validated_building_damage_function_id': 680,
            'validated_contents_damage_function_id': 427,
            'validated_inventory_damage_function_id': None # undefined for residential
        },
    ]
    
    return pd.DataFrame(sample_data)


def test_lookup_table_generation_structures(sample_structures):
    """Test that lookup table generation was performed correctly using sampled data and validated outputs"""
    
    # load the production-ready structure lookup table
    df_lookup = pd.read_csv('src/inland_consequences/data/df_lookup_structures.csv')

    # use the sample data and production-ready lookup table to assign damage function IDs
    for idx, row in sample_structures.iterrows():
        mask = (
            (df_lookup['construction_type'] == row['construction_type']) &
            (df_lookup['occupancy_type'] == row['occupancy_type']) &
            (df_lookup['story_min'] <= row['num_stories']) &
            (df_lookup['story_max'] >= row['num_stories']) &
            ((df_lookup['sqft_min'].isna()) | (df_lookup['sqft_min'] <= row['sqft'])) &
            ((df_lookup['sqft_max'].isna()) | (df_lookup['sqft_max'] >= row['sqft'])) &
            (df_lookup['foundation_type'] == row['foundation_type']) &
            (df_lookup['flood_peril_type'] == row['flood_peril_type'])
        )
        matched_row = df_lookup[mask]
        if not matched_row.empty:
            sample_structures.at[idx, 'damage_function_id'] = matched_row['damage_function_id'].values[0]
        else:
            sample_structures.at[idx, 'damage_function_id'] = None

    # validate the assigned damage function IDs
    # Convert to float64 to handle None/NaN consistently
    expected = sample_structures['validated_building_damage_function_id'].astype('float64')
    actual = sample_structures['damage_function_id'].astype('float64')
    
    pd.testing.assert_series_equal(
        actual,
        expected,
        check_names=False
    )

def test_lookup_table_generation_contents(sample_structures):
    """Test that lookup table generation was performed correctly using sampled data and validated outputs"""
    
    # load the production-ready structure lookup table
    df_lookup = pd.read_csv('src/inland_consequences/data/df_lookup_contents.csv')

    # use the sample data and production-ready lookup table to assign damage function IDs
    for idx, row in sample_structures.iterrows():
        mask = (
            (df_lookup['construction_type'] == row['construction_type']) &
            (df_lookup['occupancy_type'] == row['occupancy_type']) &
            (df_lookup['story_min'] <= row['num_stories']) &
            (df_lookup['story_max'] >= row['num_stories']) &
            ((df_lookup['sqft_min'].isna()) | (df_lookup['sqft_min'] <= row['sqft'])) &
            ((df_lookup['sqft_max'].isna()) | (df_lookup['sqft_max'] >= row['sqft'])) &
            (df_lookup['foundation_type'] == row['foundation_type']) &
            (df_lookup['flood_peril_type'] == row['flood_peril_type'])
        )
        matched_row = df_lookup[mask]
        if not matched_row.empty:
            sample_structures.at[idx, 'damage_function_id'] = matched_row['damage_function_id'].values[0]
        else:
            sample_structures.at[idx, 'damage_function_id'] = None

    # validate the assigned damage function IDs
    # Convert to float64 to handle None/NaN consistently
    expected = sample_structures['validated_contents_damage_function_id'].astype('float64')
    actual = sample_structures['damage_function_id'].astype('float64')
    
    pd.testing.assert_series_equal(
        actual,
        expected,
        check_names=False
    )

def test_lookup_table_generation_inventory(sample_structures):
    """Test that lookup table generation was performed correctly using sampled data and validated outputs"""
    
    # load the production-ready structure lookup table
    df_lookup = pd.read_csv('src/inland_consequences/data/df_lookup_inventory.csv')

    # use the sample data and production-ready lookup table to assign damage function IDs
    for idx, row in sample_structures.iterrows():
        mask = (
            (df_lookup['occupancy_type'] == row['occupancy_type']) &
            (df_lookup['foundation_type'] == row['foundation_type']) &
            (df_lookup['flood_peril_type'] == row['flood_peril_type'])
        )
        matched_row = df_lookup[mask]
        if not matched_row.empty:
            sample_structures.at[idx, 'damage_function_id'] = matched_row['damage_function_id'].values[0]
        else:
            sample_structures.at[idx, 'damage_function_id'] = None

    # validate the assigned damage function IDs
    # Convert to float64 to handle None/NaN consistently
    expected = sample_structures['validated_inventory_damage_function_id'].astype('float64')
    actual = sample_structures['damage_function_id'].astype('float64')
    
    pd.testing.assert_series_equal(
        actual,
        expected,
        check_names=False
    )
        
