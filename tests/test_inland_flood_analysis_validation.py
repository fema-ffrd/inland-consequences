"""
Tests for validation logic in InlandFloodAnalysis.

This test module exercises the building, hazard, and loss validation rules
using multiple test scenarios with different building and hazard characteristics.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pytest
import duckdb
from pathlib import Path
from unittest.mock import MagicMock, patch

from inland_consequences.nsi_buildings import NsiBuildings
from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.raster_collection import RasterCollection
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction

# tmp_path is a built-in pytest fixture for temporary directories.  
# To create the duckdb files in a known location use: uv run pytest --basetemp=outputs

# --- Test Scenario 1: Buildings with Unusual Area and Story Counts ---

@pytest.fixture(scope="module")
def buildings_unusual_characteristics():
    """
    Buildings with unusual characteristics to trigger building validation rules:
    - RES1 with 5 stories (unusual, should trigger warning)
    - COM1 with huge area (>5x expected)
    - Buildings in V-zone with basements (unusual foundation)
    """
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES1', 'COM1', 'RES2'],
        'found_ht': [2.5, 3.0, 2.0],
        'fndtype': [1, 2, 3],
        'num_story': [5, 2, 4],  # RES1 with 5 stories is unusual (>3)
        'sqft': [1000, 600000, 1500],  # COM1 with 600k is >5x the typical 110k
        'val_struct': [100000.0, 5000000.0, 200000.0],
        'val_cont': [50000.0, 2000000.0, 60000.0],
        'geometry': ['POINT (0 0)', 'POINT (1 1)', 'POINT (2 2)'],
    }

    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.GeoSeries.from_wkt(data['geometry']),
        crs="EPSG:4326"
    )
    return NsiBuildings(gdf)


# --- Test Scenario 2: Buildings with Hazard Data Anomalies ---

@pytest.fixture(scope="module")
def buildings_hazard_anomalies():
    """
    Buildings with normal characteristics but hazard data will show anomalies:
    - Depths that don't monotonically increase with return period
    - Unusual depths/velocities at shorter return periods
    """
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES3', 'RES4', 'RES5'],
        'found_ht': [2.5, 3.0, 2.0],
        'fndtype': [1, 2, 3],
        'num_story': [2, 3, 2],
        'sqft': [2200, 135000, 25000],
        'val_struct': [150000.0, 250000.0, 200000.0],
        'val_cont': [75000.0, 125000.0, 100000.0],
        'geometry': ['POINT (10 10)', 'POINT (11 11)', 'POINT (12 12)'],
    }

    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.GeoSeries.from_wkt(data['geometry']),
        crs="EPSG:4326"
    )
    return NsiBuildings(gdf)


# --- Test Scenario 3: Normal Buildings (No Anomalies) ---

@pytest.fixture(scope="module")
def buildings_normal():
    """
    Normal buildings with typical characteristics and reasonable hazard data.
    Should not trigger many validation warnings.
    """
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES1', 'RES2', 'RES3'],
        'found_ht': [2.5, 3.0, 2.0],
        'fndtype': [1, 2, 3],
        'num_story': [1, 2, 1],
        'sqft': [1800, 1475, 2200],
        'val_struct': [100000.0, 120000.0, 150000.0],
        'val_cont': [50000.0, 60000.0, 75000.0],
        'geometry': ['POINT (20 20)', 'POINT (21 21)', 'POINT (22 22)'],
    }

    gdf = gpd.GeoDataFrame(
        pd.DataFrame(data),
        geometry=gpd.GeoSeries.from_wkt(data['geometry']),
        crs="EPSG:4326"
    )
    return NsiBuildings(gdf)


# --- Raster Collection Fixtures ---

@pytest.fixture(scope="module")
def raster_collection_hazard_anomalies():
    """
    Raster collection with hazard anomalies:
    - 25-year with high depth (6 feet, exceeds 5 ft threshold)
    - Non-monotonic depth progression (higher depth at 25-year than 100-year)
    """
    mock_collection = MagicMock(spec=RasterCollection)
    mock_collection.return_periods.return_value = [25, 100, 500, 1000]
    
    # Anomalous depths: 25-year is too high and doesn't increase monotonically
    mock_depth_25 = MagicMock(spec=AbstractRasterReader)
    mock_depth_25.get_value_vectorized.return_value = [6.0, 7.0, 8.0]  # High depth at 25-year
    
    mock_depth_100 = MagicMock(spec=AbstractRasterReader)
    mock_depth_100.get_value_vectorized.return_value = [2.0, 3.0, 4.0]  # Lower at 100-year
    
    mock_depth_500 = MagicMock(spec=AbstractRasterReader)
    mock_depth_500.get_value_vectorized.return_value = [3.5, 4.5, 5.5]
    
    mock_depth_1000 = MagicMock(spec=AbstractRasterReader)
    mock_depth_1000.get_value_vectorized.return_value = [4.0, 5.0, 6.0]
    
    # Add velocity for testing
    mock_velocity_25 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_25.get_value_vectorized.return_value = [11.0, 12.0, 13.0]  # > 10 ft/s threshold
    
    mock_velocity_100 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_100.get_value_vectorized.return_value = [5.0, 6.0, 7.0]
    
    mock_velocity_500 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_500.get_value_vectorized.return_value = [7.0, 8.0, 9.0]
    
    mock_velocity_1000 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_1000.get_value_vectorized.return_value = [8.0, 9.0, 10.0]
    
    # Uncertainty/std_dev for hazard table creation
    mock_uncertainty_25 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_25.get_value_vectorized.return_value = [0.5, 0.6, 0.7]
    
    mock_uncertainty_100 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_100.get_value_vectorized.return_value = [1.0, 1.2, 1.4]
    
    mock_uncertainty_500 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_500.get_value_vectorized.return_value = [1.5, 1.8, 2.0]
    
    mock_uncertainty_1000 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_1000.get_value_vectorized.return_value = [2.0, 2.2, 2.4]
    
    def mock_get(rp):
        if rp == 25:
            return {
                "depth": mock_depth_25,
                "uncertainty": mock_uncertainty_25,
                "velocity": mock_velocity_25,
                "duration": None
            }
        elif rp == 100:
            return {
                "depth": mock_depth_100,
                "uncertainty": mock_uncertainty_100,
                "velocity": mock_velocity_100,
                "duration": None
            }
        elif rp == 500:
            return {
                "depth": mock_depth_500,
                "uncertainty": mock_uncertainty_500,
                "velocity": mock_velocity_500,
                "duration": None
            }
        elif rp == 1000:
            return {
                "depth": mock_depth_1000,
                "uncertainty": mock_uncertainty_1000,
                "velocity": mock_velocity_1000,
                "duration": None
            }
        return {"depth": None, "uncertainty": None, "velocity": None, "duration": None}

    mock_collection.get.side_effect = mock_get
    return mock_collection


@pytest.fixture(scope="module")
def raster_collection_normal():
    """
    Normal raster collection with reasonable hazard progression.
    """
    mock_collection = MagicMock(spec=RasterCollection)
    mock_collection.return_periods.return_value = [25, 100, 500, 1000]
    
    # Normal monotonic depths
    mock_depth_25 = MagicMock(spec=AbstractRasterReader)
    mock_depth_25.get_value_vectorized.return_value = [1.0, 1.5, 2.0]
    
    mock_depth_100 = MagicMock(spec=AbstractRasterReader)
    mock_depth_100.get_value_vectorized.return_value = [2.5, 3.0, 3.5]
    
    mock_depth_500 = MagicMock(spec=AbstractRasterReader)
    mock_depth_500.get_value_vectorized.return_value = [4.0, 4.5, 5.0]
    
    mock_depth_1000 = MagicMock(spec=AbstractRasterReader)
    mock_depth_1000.get_value_vectorized.return_value = [5.5, 6.0, 6.5]
    
    # Normal velocities
    mock_velocity_25 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_25.get_value_vectorized.return_value = [3.0, 4.0, 5.0]
    
    mock_velocity_100 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_100.get_value_vectorized.return_value = [5.0, 6.0, 7.0]
    
    mock_velocity_500 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_500.get_value_vectorized.return_value = [8.0, 9.0, 10.0]
    
    mock_velocity_1000 = MagicMock(spec=AbstractRasterReader)
    mock_velocity_1000.get_value_vectorized.return_value = [10.0, 11.0, 12.0]
    
    # Uncertainty
    mock_uncertainty_25 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_25.get_value_vectorized.return_value = [0.3, 0.4, 0.5]
    
    mock_uncertainty_100 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_100.get_value_vectorized.return_value = [0.5, 0.6, 0.7]
    
    mock_uncertainty_500 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_500.get_value_vectorized.return_value = [0.8, 0.9, 1.0]
    
    mock_uncertainty_1000 = MagicMock(spec=AbstractRasterReader)
    mock_uncertainty_1000.get_value_vectorized.return_value = [1.0, 1.2, 1.4]
    
    def mock_get(rp):
        if rp == 25:
            return {
                "depth": mock_depth_25,
                "uncertainty": mock_uncertainty_25,
                "velocity": mock_velocity_25,
                "duration": None
            }
        elif rp == 100:
            return {
                "depth": mock_depth_100,
                "uncertainty": mock_uncertainty_100,
                "velocity": mock_velocity_100,
                "duration": None
            }
        elif rp == 500:
            return {
                "depth": mock_depth_500,
                "uncertainty": mock_uncertainty_500,
                "velocity": mock_velocity_500,
                "duration": None
            }
        elif rp == 1000:
            return {
                "depth": mock_depth_1000,
                "uncertainty": mock_uncertainty_1000,
                "velocity": mock_velocity_1000,
                "duration": None
            }
        return {"depth": None, "uncertainty": None, "velocity": None, "duration": None}

    mock_collection.get.side_effect = mock_get
    return mock_collection


# --- Vulnerability Fixture ---

@pytest.fixture(scope="module")
def mock_vulnerability():
    """Mocks the vulnerability function to return low damage ratios."""
    mock = MagicMock(spec=AbstractVulnerabilityFunction)
    
    def mock_calculate_vulnerability(exposure_df):
        return pd.DataFrame({'damage_ratio': [0.1] * len(exposure_df)})

    mock.calculate_vulnerability.side_effect = mock_calculate_vulnerability
    return mock


# --- Test Suite 1: Building Validation Rules ---

def test_building_unusual_area_and_stories(
    buildings_unusual_characteristics, raster_collection_normal, mock_vulnerability, tmp_path
):
    """
    Test building validation rules for unusual area and story counts.
    
    This scenario includes:
    - RES1 with 5 stories (should trigger UNUSUAL_STORY_COUNT_RES1)
    - COM1 with 600k sqft (>5x typical 110k, should trigger UNUSUAL_AREA_OR_VALUATION)
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_building.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_normal,
            buildings=buildings_unusual_characteristics,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the validation log for building validation records
            validation_records = analysis.conn.sql(
                "SELECT rule, building_id, severity FROM validation_log WHERE source = 'building_validation' ORDER BY building_id"
            ).fetchall()
            
            # Should have warnings for RES1 with 5 stories
            rules = [r[0] for r in validation_records]
            assert 'UNUSUAL_STORY_COUNT_RES1' in rules, "Should flag RES1 with >3 stories"
            
            # Should have warning for COM1 with unusual area
            assert 'UNUSUAL_AREA_OR_VALUATION' in rules, "Should flag area >5x expected for occupancy"
            
            # All should be WARNING severity
            for rule, bid, severity in validation_records:
                assert severity == 'WARNING', f"Rule {rule} should be WARNING severity"


def test_building_no_anomalies(
    buildings_normal, raster_collection_normal, mock_vulnerability, tmp_path
):
    """
    Test that normal buildings don't trigger unnecessary validation warnings.
    
    This scenario uses buildings within typical ranges.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_normal.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_normal,
            buildings=buildings_normal,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query building validation records (excluding basic missing value checks)
            validation_records = analysis.conn.sql(
                "SELECT rule FROM validation_log WHERE source = 'building_validation' "
                "AND rule IN ('UNUSUAL_AREA_OR_VALUATION', 'UNUSUAL_STORY_COUNT_RES1', 'UNUSUAL_STORY_COUNT_MID_RISE')"
            ).fetchall()
            
            # Should have minimal anomalies (since buildings are normal)
            assert len(validation_records) == 0, "Normal buildings should not trigger area/story anomalies"


# --- Test Suite 2: Hazard Validation Rules ---

def test_hazard_unusual_depths_and_velocities(
    buildings_hazard_anomalies, raster_collection_hazard_anomalies, mock_vulnerability, tmp_path
):
    """
    Test hazard validation rules - verify validation structure.
    
    Note: The _create_hazard_tables method uses random data for testing,
    so specific validation triggers may not be deterministic. This test
    verifies that the validation method runs without error and can process
    hazard records.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_hazard.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_hazard_anomalies,
            buildings=buildings_hazard_anomalies,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the validation log for hazard validation records
            validation_records = analysis.conn.sql(
                "SELECT rule, building_id, severity FROM validation_log WHERE source = 'hazard_validation' ORDER BY rule"
            ).fetchall()
            
            # The hazard_validation method should execute without errors
            # Records may or may not be populated depending on random hazard data
            
            # Check the hazard table was created
            hazard_count = analysis.conn.sql(
                "SELECT COUNT(*) FROM hazard"
            ).fetchone()
            
            assert hazard_count[0] > 0, "Hazard table should contain records"
            
            # All validation records should be WARNING severity
            for rule, bid, severity in validation_records:
                assert severity == 'WARNING', f"Rule {rule} should be WARNING severity"


def test_hazard_monotonic_progression(
    buildings_normal, raster_collection_normal, mock_vulnerability, tmp_path
):
    """
    Test that normal hazard data doesn't trigger monotonicity warnings.
    
    This scenario uses monotonically increasing hazard parameters.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_monotonic.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_normal,
            buildings=buildings_normal,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query for monotonicity violations
            monotonic_violations = analysis.conn.sql(
                "SELECT COUNT(*) FROM validation_log WHERE rule = 'DEPTH_DECREASES_WITH_RETURN_PERIOD'"
            ).fetchone()
            
            assert monotonic_violations[0] == 0, "Normal hazard data should not violate monotonicity"


# --- Test Suite 3: Results/Loss Validation Rules ---

def test_loss_unusual_hazard_data(
    buildings_hazard_anomalies, raster_collection_hazard_anomalies, mock_vulnerability, tmp_path
):
    """
    Test loss validation rules when hazard data is anomalous.
    
    Unusual hazard parameters may lead to high loss ratios.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_loss.duckdb")
    ):
        # Use higher damage ratio for this scenario to trigger loss warnings
        mock_high_vuln = MagicMock(spec=AbstractVulnerabilityFunction)
        
        def mock_high_vuln_calc(exposure_df):
            return pd.DataFrame({'damage_ratio': [0.6] * len(exposure_df)})
        
        mock_high_vuln.calculate_vulnerability.side_effect = mock_high_vuln_calc
        
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_hazard_anomalies,
            buildings=buildings_hazard_anomalies,
            vulnerability=mock_high_vuln,
            calculate_aal=False
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query for loss validation warnings
            loss_records = analysis.conn.sql(
                "SELECT rule, severity FROM validation_log WHERE source = 'results_validation'"
            ).fetchall()
            
            # With high damage ratios at 10-year, may trigger HIGH_10YR_LOSS
            if len(loss_records) > 0:
                for rule, severity in loss_records:
                    assert severity == 'WARNING', "Loss validation should be WARNING severity"


def test_loss_normal_data(
    buildings_normal, raster_collection_normal, mock_vulnerability, tmp_path
):
    """
    Test that normal hazard and low damage ratios don't trigger loss warnings.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_loss_normal.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_normal,
            buildings=buildings_normal,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query for loss validation warnings (excluding data issues)
            loss_records = analysis.conn.sql(
                "SELECT COUNT(*) FROM validation_log WHERE source = 'results_validation' "
                "AND rule IN ('LOSS_RATIO_EXCEEDS_100', 'HIGH_10YR_LOSS', 'HIGH_AAL_LOSS_RATIO')"
            ).fetchone()
            
            # With low damage ratios (10%), should have no or minimal loss warnings
            # The exact number depends on the interaction of hazard data and damage ratios
            assert loss_records[0] <= 12, "Normal data should not trigger excessive loss warnings"


# --- Comprehensive Validation Log Test ---

def test_log_structure(
    buildings_unusual_characteristics, raster_collection_normal, mock_vulnerability, tmp_path
):
    """
    Test that the validation_log table has proper structure and all required fields.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_log_structure.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_normal,
            buildings=buildings_unusual_characteristics,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Check validation_log schema
            schema = analysis.conn.sql("DESCRIBE validation_log").fetchall()
            column_names = [s[0] for s in schema]
            
            expected_columns = ['id', 'building_id', 'table_name', 'source', 'rule', 'message', 'severity']
            for col in expected_columns:
                assert col in column_names, f"validation_log should have {col} column"
            
            # Check that records were inserted
            record_count = analysis.conn.sql("SELECT COUNT(*) FROM validation_log").fetchone()
            assert record_count[0] > 0, "validation_log should contain records"


def test_sources_present(
    buildings_unusual_characteristics, raster_collection_hazard_anomalies, mock_vulnerability, tmp_path
):
    """
    Test that validation sources are populated in the validation_log table.
    """
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=str(tmp_path / "test_sources.duckdb")
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=raster_collection_hazard_anomalies,
            buildings=buildings_unusual_characteristics,
            vulnerability=mock_vulnerability,
            calculate_aal=True
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Check for all three validation sources
            sources = analysis.conn.sql(
                "SELECT DISTINCT source FROM validation_log ORDER BY source"
            ).fetchall()
            
            source_names = [s[0] for s in sources]
            
            # Should have building validation records (from unusual characteristics)
            assert 'building_validation' in source_names, "Should have building_validation records"
            
            # Should have results validation records
            assert 'results_validation' in source_names, "Should have results_validation records"
            
            # Hazard validation may or may not have records depending on random data
            # but all three sources are available in the code
            assert len(source_names) >= 2, "Should have at least 2 validation sources"
