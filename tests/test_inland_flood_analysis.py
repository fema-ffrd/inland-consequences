import numpy as np
import pandas as pd
import geopandas as gpd
import pytest

import duckdb
from unittest.mock import MagicMock
from inland_consequences.nsi_buildings import NsiBuildings

from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.raster_collection import RasterCollection
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction

# --- Fixtures for Mocking External Dependencies ---

@pytest.fixture(scope="module")
def mock_buildings():
    """Provides a real NsiBuildings object with a small, fixed GeoDataFrame."""
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES1', 'RES1', 'COM1'],
        'found_ht': [2.5, 3.0, 2.0],
        'fndtype': [7, 4, 1],  # 7=Slab->S->SLAB, 4=Basement->B->BASE, 1=Pile->I->PILE
        'num_story': [1, 2, 2],
        'sqft': [1000, 1500, 1200],
        'val_struct': [100000.0, 200000.0, 300000.0],
        'val_cont': [50000.0, 60000.0, 70000.0],
        'geometry': ['POINT (0 0)', 'POINT (1 1)', 'POINT (2 2)'],
    }

    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.GeoSeries.from_wkt(data['geometry']),
        crs="EPSG:4326"
    )
    return NsiBuildings(gdf)

@pytest.fixture(scope="module")
def mock_raster_collection():
    """Mocks the RasterCollection to return predictable depths."""
    mock_collection = MagicMock(spec=RasterCollection)
    
    # Define the depths to be returned based on the return period (RP)
    # RP 100: depths 1.0, 2.0, 3.0
    # RP 500: depths 1.5, 2.5, 3.5
    
    mock_collection.return_periods.return_value = [100, 500]
    
    # Create mock depth rasters for each return period
    mock_depth_100 = MagicMock(spec=AbstractRasterReader)
    mock_depth_100.get_value_vectorized.return_value = [1.0, 2.0, 3.0]
    
    mock_depth_500 = MagicMock(spec=AbstractRasterReader)
    mock_depth_500.get_value_vectorized.return_value = [1.5, 2.5, 3.5]
    
    def mock_get(rp):
        if rp == 100:
            return {"depth": mock_depth_100, "uncertainty": None, "velocity": None, "duration": None}
        elif rp == 500:
            return {"depth": mock_depth_500, "uncertainty": None, "velocity": None, "duration": None}
        return {"depth": None, "uncertainty": None, "velocity": None, "duration": None}

    mock_collection.get.side_effect = mock_get
    return mock_collection

@pytest.fixture(scope="module")
def mock_vulnerability():
    """Mocks the vulnerability function to return a fixed damage ratio."""
    mock = MagicMock(spec=AbstractVulnerabilityFunction)
    
    def mock_calculate_vulnerability(exposure_df):
        # Always return a fixed 50% damage ratio for simplicity in tests
        return pd.DataFrame({'damage_ratio': [0.5] * len(exposure_df)})

    mock.calculate_vulnerability.side_effect = mock_calculate_vulnerability
    return mock

# Identifier for testing
IN_MEMORY_DB_NAME = ':memory:integration_test_db'

@pytest.fixture(scope="module") # Run once for all tests in this file
def flood_analysis_results(mock_raster_collection, mock_buildings, mock_vulnerability):
    """
    1. Patches the DB identifier to use a shared named in-memory DB.
    2. Instantiates the InlandFloodAnalysis.
    3. Runs the expensive 'calculate_losses' method once to populate the DB.
    4. Yields the connected analysis for assertions.
    """
    from unittest.mock import patch
    
    # 1. Patch the identifier (HACK)
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier", 
        return_value=IN_MEMORY_DB_NAME
    ):
        # 2. Instantiate and use the context manager
        analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=mock_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        # 3. Enter the context manager to open the connection and setup tables
        with analysis:
            # **This is where the expensive data-creating call happens ONCE**
            analysis.calculate_losses()
            
            # 4. Yield the connected instance for the tests to use
            yield analysis
        
    # 5. Cleanup (runs after all tests in the module are complete)
    # The __exit__ method in the DataProcessor handles the conn.close()

@pytest.mark.manual
def test_manual_calculate_losses(mock_raster_collection, mock_buildings, mock_vulnerability):
    # To run this test manually, execute the statement in the command line
    # uv run pytest -m manual tests/test_inland_flood_analysis.py
    
    analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=mock_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
    # 3. Enter the context manager to open the connection and setup tables
    with analysis:
        # **This is where the expensive data-creating call happens ONCE**
        analysis.calculate_losses()

def test_buildings_copied(flood_analysis_results):
    """Test that buildings data is copied into the analysis database."""
    conn = flood_analysis_results.conn
    
    result = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()
    assert result[0] == 3  # We had 3 buildings in the mock

def test_calculate_losses_duckdb(flood_analysis_results):
    """Test that _calculate_losses can use a DuckDB connection if provided."""
    conn = flood_analysis_results.conn
    
    assert conn is not None

def test_gather_damage_functions(flood_analysis_results):
    """Test that structure_damage_functions table is created with correct schema and data."""
    conn = flood_analysis_results.conn
    
    # Check that table exists and has data
    result = conn.execute("SELECT COUNT(*) FROM structure_damage_functions").fetchone()
    assert result[0] > 0, "structure_damage_functions table should have at least one row"
    
    # Show the structure_damage_functions table
    print("\n=== structure_damage_functions table ===")
    df = conn.execute("SELECT * FROM structure_damage_functions ORDER BY building_id, damage_function_id").fetchdf()
    print(df.to_string())
    
    # Check schema has expected columns
    columns = conn.execute("DESCRIBE structure_damage_functions").fetchdf()
    expected_columns = {'building_id', 'damage_function_id', 'first_floor_height', 'ffh_sig', 'weight'}
    actual_columns = set(columns['column_name'].tolist())
    assert expected_columns.issubset(actual_columns), f"Missing columns: {expected_columns - actual_columns}"
    
    # Check that each building has at least one damage function
    building_counts = conn.execute("""
        SELECT building_id, COUNT(*) as curve_count
        FROM structure_damage_functions
        GROUP BY building_id
    """).fetchdf()
    assert len(building_counts) == 3, "Should have damage functions for all 3 buildings"
    assert all(building_counts['curve_count'] > 0), "Each building should have at least one damage function"
    
    # Check that weights sum to 1.0 per building
    weight_sums = conn.execute("""
        SELECT building_id, SUM(weight) as total_weight
        FROM structure_damage_functions
        GROUP BY building_id
    """).fetchdf()
    for _, row in weight_sums.iterrows():
        assert abs(row['total_weight'] - 1.0) < 0.01, f"Weights for building {row['building_id']} should sum to 1.0"
    
    # Check that first_floor_height values are preserved from buildings table
    ffh_check = conn.execute("""
        SELECT DISTINCT sdf.building_id, sdf.first_floor_height, b.first_floor_height as original_ffh
        FROM structure_damage_functions sdf
        JOIN buildings b ON sdf.building_id = b.ID
    """).fetchdf()
    for _, row in ffh_check.iterrows():
        assert row['first_floor_height'] == row['original_ffh'], f"first_floor_height should match for building {row['building_id']}"
    
    # Check that ffh_sig is 0 (as specified)
    ffh_sig_check = conn.execute("SELECT DISTINCT ffh_sig FROM structure_damage_functions").fetchone()
    assert ffh_sig_check[0] == 0, "ffh_sig should be 0"
    
    # Now we can test the losses
    