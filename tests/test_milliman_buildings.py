import pandas as pd
import geopandas as gpd
import pytest

from inland_consequences.milliman_buildings import MillimanBuildings


@pytest.fixture
def milliman_sample_gdf():
    """
    Create a sample GeoDataFrame with Milliman-specific column names.
    
    Based on milliman uniform sample data from Maryland and typical columns:
    BLDG_VALUE, CNT_VALUE, NUM_STORIE, foundation, FIRST_FLOO
    """
    df = pd.DataFrame({
        "location": ["MD00414640", "MD01230741", "MD00255922"],  # Can serve as "id" alias
        # "occupancy_type": ["RES1", "RES1", "COM1"],  # Required field, but not provided from source
        # "area": [1800, 1800, 2500],  # Required field, but not provided from source
        "BLDG_VALUE": [200000, 200000, 200000],
        "CNT_VALUE": [50000, 50000, 50000],
        "BLDG_LIMIT": [200000, 200000, 200000],
        "CNT_LIM": [50000, 50000, 50000],
        "NUM_STORIE": [1, 1, 1],
        "BLDG_DED": [1500, 1500, 1500],
        "CNT_DED": [1500, 1500, 1500],
        "foundation": [8, 8, 8],
        "BasementFi": [0, 0, 0],
        "FIRST_FLOO": [1, 1, 1],
        "DEMft": [13.419362, 244.269119, 224.764328],
        # longitude and latitude not in original fields, but assumed present as a geospatial file
        "Longitude": [-76.27738, -76.49555, -76.93276],
        "Latitude": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.Longitude, df.Latitude), 
        crs="EPSG:4326"
    )
    return gdf

@pytest.fixture
def milliman_sample_gdf_missing_values():
    """
    Create a sample GeoDataFrame with Milliman-specific column names and some missing values.
    """
    df = pd.DataFrame({
        "location": ["MD00414640", "MD01230741", "MD00255922"], # Can serve as "id" alias
        # "occupancy_type": ["RES1", "RES1", "COM1"],  # Required field, but not provided from source
        # "area": [1800, 1800, 2500],  # Required field, but not provided from source
        "BLDG_VALUE": [200000, None, 250000],
        "CNT_VALUE": [50000, 60000, None],
        "NUM_STORIE": [1, None, 2],
        "foundation": [8, 8, None],
        "BasementFi": [0, 0, 0],
        "FIRST_FLOO": [1, 1, 1],
        "DEMft": [13.419362, 244.269119, None],
        # longitude and latitude not in original fields, but assumed present as a geospatial file
        "Longitude": [-76.27738, -76.49555, -76.93276],
        "Latitude": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.Longitude, df.Latitude), 
        crs="EPSG:4326"
    )
    return gdf

@pytest.fixture
def milliman_sample_gdf_missing_required_fields():
    """
    Create a sample GeoDataFrame missing REQUIRED fields (BLDG_VALUE).
    """
    df = pd.DataFrame({
        "location": ["MD00414640", "MD01230741", "MD00255922"],  # Can serve as "id" alias
        # "occupancy_type": ["RES1", "RES1", "COM1"],  # Required field, but not provided from source
        # "area": [1800, 1800, 2500],  # Required field, but not provided from source
        # "BLDG_VALUE": [200000, 200000, 200000], # MOCKING A MISSING REQUIRED FIELD
        "CNT_VALUE": [50000, 50000, 50000],
        "BLDG_LIMIT": [200000, 200000, 200000],
        "CNT_LIM": [50000, 50000, 50000],
        "NUM_STORIE": [1, 1, 1],
        "BLDG_DED": [1500, 1500, 1500],
        "CNT_DED": [1500, 1500, 1500],
        "foundation": [8, 8, 8],
        "BasementFi": [0, 0, 0],
        "FIRST_FLOO": [1, 1, 1],
        "DEMft": [13.419362, 244.269119, 224.764328],
        # longitude and latitude not in original fields, but assumed present as a geospatial file
        "Longitude": [-76.27738, -76.49555, -76.93276],
        "Latitude": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.Longitude, df.Latitude), 
        crs="EPSG:4326"
    )
    return gdf

def test_load_valid_milliman_data(milliman_sample_gdf):
    """Test that MillimanBuildings can be instantiated with Milliman data."""
    mb = MillimanBuildings(milliman_sample_gdf)
    
    # Assert that the underlying GeoDataFrame has the expected records
    assert len(mb.gdf) == 3


def test_milliman_building_cost_mapping(milliman_sample_gdf):
    """Test that BLDG_VALUE is correctly mapped to building_cost using the Milliman defaults."""
    mb = MillimanBuildings(milliman_sample_gdf)
    
    # Access building_cost through the property
    costs = mb.building_cost
    
    # Should return values from BLDG_VALUE column
    assert len(costs) == 3
    assert costs.iloc[0] == 200000
    assert all(costs == 200000)

def test_milliman_field_mapping_visible(milliman_sample_gdf):
    """Test that we can see the field mapping based on Milliman defaults."""
    mb = MillimanBuildings(milliman_sample_gdf)
    
    # Check that the mappings are as expected
    assert mb.fields.get_field_name("building_cost") == "BLDG_VALUE"
    assert mb.fields.get_field_name("content_cost") == "CNT_VALUE"
    assert mb.fields.get_field_name("number_stories") == "NUM_STORIE"
    assert mb.fields.get_field_name("foundation_type") == "foundation"
    assert mb.fields.get_field_name("first_floor_height") == "FIRST_FLOO"

def test_milliman_with_user_overrides(milliman_sample_gdf):
    """Test that user overrides take precedence over Milliman defaults."""
    # Add a custom cost column
    milliman_sample_gdf["MY_CUSTOM_COST"] = [300000, 350000, 400000]
    
    # User wants to use their custom column for building_cost
    user_overrides = {"building_cost": "MY_CUSTOM_COST"}
    
    mb = MillimanBuildings(milliman_sample_gdf, overrides=user_overrides)
    
    # Should use the custom column, not BLDG_VALUE
    costs = mb.building_cost
    assert costs.iloc[0] == 300000
    assert costs.iloc[1] == 350000
    assert costs.iloc[2] == 400000

def test_milliman_impute_missing_values(milliman_sample_gdf):
    """Test that the area field is generated with default values (not in standard Milliman data)."""
    mb = MillimanBuildings(milliman_sample_gdf)
    
    # check that occupancy_type field was generated and has no missing values and that records have default value
    assert mb.occupancy_type is not None
    assert not mb.occupancy_type.isna().any()
    assert all(mb.occupancy_type == "RES1")

    # Check that area field was generated and has no missing values and that records have default value
    assert mb.area is not None
    assert not mb.area.isna().any()
    assert all(mb.area == 1800)

def test_milliman_missing_required_fields(milliman_sample_gdf_missing_required_fields):
    """Test that having missing required Milliman fields raises an error."""
    with pytest.raises(ValueError):
        mb = MillimanBuildings(milliman_sample_gdf_missing_required_fields)

def test_milliman_required_fields_nans(milliman_sample_gdf_missing_values):
    """Test that having missing values in required fields raises an error."""
    with pytest.raises(ValueError):
        mb = MillimanBuildings(milliman_sample_gdf_missing_values)

