"""
Test wildcard field functionality in damage function matching.

This test demonstrates how to use the wildcard_fields parameter to 
control which building attributes are used for matching damage functions.
"""

import numpy as np
import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import MagicMock

from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from inland_consequences.nsi_buildings import NsiBuildings
from inland_consequences.raster_collection import RasterCollection
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction


@pytest.fixture(scope="module")
def sample_buildings():
    """Create sample buildings with various attributes."""
    data = {
        'target_fid': [1, 2, 3],
        'occtype': ['RES1', 'RES1', 'RES1'],  # All same occupancy
        'bldgtype': ['W', 'M', 'S'],  # Different construction types
        'found_ht': [2.5, 3.0, 2.0],
        'found_type': ['S', 'C', 'I'],  # Different foundation types (Slab, Crawl, Pile)
        'num_story': [1, 2, 6],  # Different story counts
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
    """Mock raster collection for testing."""
    mock_collection = MagicMock(spec=RasterCollection)
    mock_collection.return_periods.return_value = [100]
    
    mock_depth = MagicMock(spec=AbstractRasterReader)
    mock_depth.get_value_vectorized.return_value = [1.0, 1.0, 1.0]
    
    mock_collection.get.return_value = {
        "depth": mock_depth,
        "uncertainty": None,
        "velocity": None,
        "duration": None
    }
    
    # Add sample_for_rp mock
    def mock_sample_for_rp(rp, geometries):
        n = len(geometries)
        idx = pd.Index(range(n))
        if rp == 100:
            return {
                "depth": pd.Series([1.0, 1.0, 1.0][:n], index=idx),
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
    """Mock vulnerability function."""
    return MagicMock(spec=AbstractVulnerabilityFunction)


def test_default_matching_all_attributes(sample_buildings, mock_raster_collection, mock_vulnerability):
    """Test default behavior - match on all attributes (no wildcards)."""
    from unittest.mock import patch
    
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=":memory:test_default"
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=sample_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=False,
            wildcard_fields=[]  # No wildcards - match on all attributes
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the results
            result = analysis.conn.execute("""
                SELECT building_id, COUNT(DISTINCT damage_function_id) as num_curves
                FROM structure_damage_functions
                GROUP BY building_id
                ORDER BY building_id
            """).fetchdf()
            
            # Each building should have potentially different numbers of matching curves
            # since they have different foundation, stories, and construction types
            assert len(result) == 3
            print("\nDefault matching (all attributes):")
            print(result)


def test_wildcard_construction_type(sample_buildings, mock_raster_collection, mock_vulnerability):
    """Test wildcarding construction type - should match more curves per building."""
    from unittest.mock import patch
    
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=":memory:test_wildcard_construction"
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=sample_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=False,
            wildcard_fields=['general_building_type']  # Ignore construction type
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the results
            result = analysis.conn.execute("""
                SELECT building_id, COUNT(DISTINCT damage_function_id) as num_curves
                FROM structure_damage_functions
                GROUP BY building_id
                ORDER BY building_id
            """).fetchdf()
            
            assert len(result) == 3
            print("\nWildcard construction type:")
            print(result)


def test_wildcard_all_optional(sample_buildings, mock_raster_collection, mock_vulnerability):
    """Test wildcarding all optional attributes - match only on occupancy type."""
    from unittest.mock import patch
    
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=":memory:test_wildcard_all"
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=sample_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=False,
            wildcard_fields=['foundation_type', 'number_stories', 'general_building_type']
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the results
            result = analysis.conn.execute("""
                SELECT building_id, COUNT(DISTINCT damage_function_id) as num_curves
                FROM structure_damage_functions
                GROUP BY building_id
                ORDER BY building_id
            """).fetchdf()
            
            # All buildings have same occupancy (RES1), so they should all match
            # the same set of curves when all other attributes are wildcarded
            assert len(result) == 3
            
            # All buildings should have the same number of matching curves
            assert result['num_curves'].nunique() == 1, "All buildings should match same curves when fully wildcarded"
            
            print("\nWildcard all except occupancy_type (match only on occupancy):")
            print(result)


def test_wildcard_occupancy_type(sample_buildings, mock_raster_collection, mock_vulnerability):
    """Test wildcarding occupancy_type - should match ALL curves regardless of occupancy."""
    from unittest.mock import patch
    
    with patch(
        "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
        return_value=":memory:test_wildcard_occupancy"
    ):
        analysis = InlandFloodAnalysis(
            raster_collection=mock_raster_collection,
            buildings=sample_buildings,
            vulnerability=mock_vulnerability,
            calculate_aal=False,
            wildcard_fields=['occupancy_type']  # Wildcard occupancy, still match on other attributes
        )
        
        with analysis:
            analysis.calculate_losses()
            
            # Query the results
            result = analysis.conn.execute("""
                SELECT building_id, COUNT(DISTINCT damage_function_id) as num_curves
                FROM structure_damage_functions
                GROUP BY building_id
                ORDER BY building_id
            """).fetchdf()
            
            assert len(result) == 3
            
            # Buildings should have more matches than the default case since
            # they can now match curves from ANY occupancy type (not just RES1)
            print("\nWildcard occupancy_type (match all occupancy types):")
            print(result)
            print(f"Total unique curves in result: {result['num_curves'].sum()}")


# def test_wildcard_everything(sample_buildings, mock_raster_collection, mock_vulnerability):
#     """Test wildcarding ALL attributes - should match every curve in the database."""
#     from unittest.mock import patch
    
#     with patch(
#         "inland_consequences.inland_flood_analysis.InlandFloodAnalysis._get_db_identifier",
#         return_value=":memory:test_wildcard_everything"
#     ):
#         analysis = InlandFloodAnalysis(
#             raster_collection=mock_raster_collection,
#             buildings=sample_buildings,
#             vulnerability=mock_vulnerability,
#             calculate_aal=False,
#             wildcard_fields=['occupancy_type', 'foundation_type', 'number_stories', 'general_building_type']
#         )
        
#         with analysis:
#             analysis.calculate_losses()
            
#             # Query the results
#             result = analysis.conn.execute("""
#                 SELECT building_id, COUNT(DISTINCT damage_function_id) as num_curves
#                 FROM structure_damage_functions
#                 GROUP BY building_id
#                 ORDER BY building_id
#             """).fetchdf()
            
#             assert len(result) == 3
            
#             # All buildings should match the exact same set of curves (all of them)
#             assert result['num_curves'].nunique() == 1, "All buildings should match identical curves when everything is wildcarded"
            
#             # Count total unique curves in the xref table
#             total_curves = analysis.conn.execute("""
#                 SELECT COUNT(DISTINCT damage_function_id) as total
#                 FROM xref_structures
#             """).fetchone()[0]
            
#             print("\nWildcard ALL attributes (match every curve):")
#             print(result)
#             print(f"Total curves in xref_structures: {total_curves}")
#             print(f"Matched curves per building: {result['num_curves'].iloc[0]}")
            
#             # Each building should match ALL curves in the database
#             assert result['num_curves'].iloc[0] == total_curves, "Should match all curves when everything wildcarded"
