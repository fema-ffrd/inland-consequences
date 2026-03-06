import numpy as np
import pandas as pd
import geopandas as gpd
import pytest

import duckdb
from unittest.mock import MagicMock, patch
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
        'occtype': ['RES1', 'RES2', 'RES3A'],
        'bldgtype': ['W', 'MH', 'M'],  # Wood, Manufactured Housing, Masonry
        'found_ht': [2.5, 3.0, 2.0],
        'found_type': ['S', 'C', 'I'],  # Slab, Crawl, Pile
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
def flood_analysis_results(tmp_path_factory, mock_raster_collection, mock_buildings, mock_vulnerability):
    """
    1. Uses a temp directory for the DB file via tmp_path_factory.
    2. Instantiates the InlandFloodAnalysis.
    3. Runs the expensive 'calculate_losses' method once to populate the DB.
    4. Yields the connected analysis for assertions.
    """
    from unittest.mock import patch
    
    db_path = str(tmp_path_factory.mktemp("flood_analysis") / "test_analysis.duckdb")

    # 1. Patch the identifier to use a temp file DB
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier", 
        return_value=db_path
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
def test_manual_calculate_losses(tmp_path):
    # To run this test manually, execute the statement in the command line
    # uv run pytest -m manual tests/test_inland_flood_analysis.py
    from pathlib import Path
    from sphere.flood.single_value_reader import SingleValueRaster
    from inland_consequences.inland_vulnerability import InlandFloodVulnerability

    examples_dir = Path(__file__).parent.parent / "examples" / "Duwamish"

    return_periods = [10, 20, 50, 100, 200, 500, 1000, 2000]
    rp_map = {}
    for rp in return_periods:
        rp_map[rp] = {
            "depth": SingleValueRaster(str(examples_dir / f"aep_mean_depth_{rp}yr_sample_EPSG4326.tif")),
            "velocity": SingleValueRaster(str(examples_dir / f"aep_mean_velocity_{rp}yr_sample_EPSG4326.tif")),
            "uncertainty": SingleValueRaster(str(examples_dir / f"aep_stdev_depth_{rp}yr_sample_EPSG4326.tif")),
        }
    raster_collection = RasterCollection(rp_map)

    nsi_gdf = gpd.read_parquet(str(examples_dir / "nsi_duwamish.parquet"))
    buildings = NsiBuildings(nsi_gdf, overrides={"id": "fd_id"})

    vulnerability = InlandFloodVulnerability(buildings=buildings)

    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_duwamish.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection,
            buildings=buildings,
            vulnerability=vulnerability,
            calculate_aal=True
        )
        
        with analysis:
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
    

def test_all_buildings_have_damage_function(flood_analysis_results):
    """Test that every building has at least one entry in structure_damage_functions."""
    conn = flood_analysis_results.conn

    unmatched = conn.execute("""
        SELECT b.id
        FROM buildings b
        LEFT JOIN structure_damage_functions sdf ON b.id = sdf.building_id
        WHERE sdf.building_id IS NULL
    """).fetchall()

    assert unmatched == [], (
        f"Buildings with no damage function assigned: {unmatched}"
    )


def test_structure_damage_functions_one_per_building(flood_analysis_results):
    """Test that each building_id has exactly one record in structure_damage_functions.

    With flood_peril_type matching enabled, each building is assigned a single
    peril type (derived from velocity/duration) which resolves to exactly one DDF.
    """
    conn = flood_analysis_results.conn

    duplicates = conn.execute("""
        SELECT building_id, COUNT(*) AS cnt
        FROM structure_damage_functions
        GROUP BY building_id
        HAVING cnt > 1
    """).fetchall()

    assert duplicates == [], (
        f"Found building_ids with multiple structure_damage_functions records: {duplicates}"
    )
    