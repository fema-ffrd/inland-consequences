import numpy as np
import pandas as pd
import geopandas as gpd
import pytest

import duckdb
from unittest.mock import MagicMock
from inland_consequences.nsi_buildings import NsiBuildings
from inland_consequences.milliman_buildings import MillimanBuildings

# tmp_path is a built-in pytest fixture for temporary directories.  
# To create the duckdb files in a known location use: uv run pytest --basetemp=outputs

from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.raster_collection import RasterCollection
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction

# --- Fixtures for Mocking External Dependencies ---

@pytest.fixture(scope="module")
def nsi_buildings():
    """Provides a real NsiBuildings object with a small, fixed GeoDataFrame."""

    # Mock Data
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES1', 'RES2', 'RES3A'],
        'bldgtype': ['W', 'MH', 'M'],  # Wood, Manufactured Housing, Masonry
        'found_ht': [2.5, 3.0, 2.0],
        'found_type': ['S', 'C', 'I'],  # Slab, Crawl, Pile (string codes)
        'num_story': [1, 2, 1],
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
def milliman_buildings():
    """Provides a real MillimanBuildings object with a small, fixed GeoDataFrame."""

    # Mock Data with Milliman schema
    data = {
        'location': ['CO00000001', 'CO00000002', 'CO00000003'],
        'BLDG_VALUE': [100000.0, 200000.0, 300000.0],
        'CNT_VALUE': [50000.0, 60000.0, 70000.0],
        'NUM_STORIES': [1, 2, 1],
        'FoundationType': [8, 8, 8],
        'FIRST_FLOOR_ELEV': [2.5, 3.0, 2.0],
        'CONSTR_CODE': [1, 2, 1],
        'LON': [-76.27738, -76.49555, -76.93276],
        'LAT': [38.96829, 39.36650, 38.79571],
    }

    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.points_from_xy(data['LON'], data['LAT']),
        crs="EPSG:4326"
    )
    return MillimanBuildings(gdf)

@pytest.fixture(scope="module", params=["nsi", "milliman"])
def mock_buildings(request, nsi_buildings, milliman_buildings):
    """Parametrized fixture that provides both NSI and Milliman building types."""
    if request.param == "nsi":
        return nsi_buildings
    elif request.param == "milliman":
        return milliman_buildings

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
    
    # Add sample_for_rp mock
    def mock_sample_for_rp(rp, geometries):
        n = len(geometries)
        idx = pd.Index(range(n))
        if rp == 100:
            return {
                "depth": pd.Series([1.0, 2.0, 3.0][:n], index=idx),
                "uncertainty": pd.Series([0.0] * n, index=idx),
                "velocity": pd.Series([np.nan] * n, index=idx),
                "duration": pd.Series([np.nan] * n, index=idx),
            }
        elif rp == 500:
            return {
                "depth": pd.Series([1.5, 2.5, 3.5][:n], index=idx),
                "uncertainty": pd.Series([0.0] * n, index=idx),
                "velocity": pd.Series([np.nan] * n, index=idx),
                "duration": pd.Series([np.nan] * n, index=idx),
            }
        return {
            "depth": pd.Series([0.0] * n, index=idx),
            "uncertainty": pd.Series([0.0] * n, index=idx),
            "velocity": pd.Series([np.nan] * n, index=idx),
            "duration": pd.Series([np.nan] * n, index=idx),
        }
    
    mock_collection.sample_for_rp.side_effect = mock_sample_for_rp
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

@pytest.fixture(scope="module") # Run once for all tests in this file
def flood_analysis_results(mock_raster_collection, mock_buildings, mock_vulnerability, tmp_path_factory):
    """
    1. Patches the DB identifier to use a file-based DB.
    2. Instantiates the InlandFloodAnalysis.
    3. Runs the expensive 'calculate_losses' method once to populate the DB.
    4. Yields the connected analysis for assertions.
    """
    from unittest.mock import patch
    
    # Create a temporary directory for this module's tests
    tmp_path = tmp_path_factory.mktemp("flood_analysis")
    
    # 1. Patch the identifier to use file-based DB
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier", 
        return_value=str(tmp_path / "test_gather_damage_functions.duckdb")
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

def test_gather_damage_functions_table_exists(flood_analysis_results):
    """Test that structure_damage_functions table is created with data."""
    conn = flood_analysis_results.conn
    
    result = conn.execute("SELECT COUNT(*) FROM structure_damage_functions").fetchone()
    assert result[0] > 0

def test_gather_damage_functions_schema(flood_analysis_results):
    """Test that structure_damage_functions table has expected columns."""
    conn = flood_analysis_results.conn
    
    columns = conn.execute("DESCRIBE structure_damage_functions").fetchdf()
    expected_columns = {'building_id', 'damage_function_id', 'first_floor_height', 'ffh_sig', 'weight'}
    actual_columns = set(columns['column_name'].tolist())
    assert expected_columns.issubset(actual_columns)

def test_all_buildings_have_damage_functions(flood_analysis_results):
    """Test that all buildings from buildings table are paired with damage functions."""
    conn = flood_analysis_results.conn
    
    unpaired = conn.execute("""
        SELECT b.ID 
        FROM buildings b
        LEFT JOIN structure_damage_functions sdf ON b.ID = sdf.building_id
        WHERE sdf.building_id IS NULL
    """).fetchdf()
    
    assert len(unpaired) == 0

def test_gather_damage_functions_weights_sum_to_one(flood_analysis_results):
    """Test that weights sum to 1.0 per building."""
    conn = flood_analysis_results.conn
    
    weight_sums = conn.execute("""
        SELECT building_id, SUM(weight) as total_weight
        FROM structure_damage_functions
        GROUP BY building_id
    """).fetchdf()
    for _, row in weight_sums.iterrows():
        assert abs(row['total_weight'] - 1.0) < 0.01

def test_gather_damage_functions_preserves_ffh(flood_analysis_results):
    """Test that first_floor_height values match the buildings table."""
    conn = flood_analysis_results.conn
    
    ffh_check = conn.execute("""
        SELECT DISTINCT sdf.building_id, sdf.first_floor_height, b.first_floor_height as original_ffh
        FROM structure_damage_functions sdf
        JOIN buildings b ON sdf.building_id = b.ID
    """).fetchdf()
    for _, row in ffh_check.iterrows():
        assert row['first_floor_height'] == row['original_ffh']


