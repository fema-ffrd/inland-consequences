import pandas as pd
import geopandas as gpd
import pytest

from inland_consequences.nsi_buildings import NsiBuildings


@pytest.fixture
def nsi_sample_gdf():
    """
    Create a sample GeoDataFrame with NSI-specific column names.
    
    Based on NSI (National Structure Inventory) typical columns:
    target_fid, occtype, found_ht, found_type (or fndtype), num_story, sqft, val_struct, val_cont
    """
    df = pd.DataFrame({
        "target_fid": ["NSI001", "NSI002", "NSI003"],
        "occtype": ["RES1-1SNB", "RES1-2SNB", "COM1-W2"],  # With suffixes to test preprocessing
        "found_ht": [2.0, 3.5, 1.0],
        "found_type": ["S", "C", "I"],  # String codes: S=Slab, C=Crawl, I=Pile
        "num_story": [1, 2, 1],
        "sqft": [1800, 2400, 5000],
        "val_struct": [250000, 350000, 500000],
        "val_cont": [75000, 100000, 150000],
        "bldgtype": ["W", "W", "C"],  # W=Wood, C=Concrete
        "x": [-76.27738, -76.49555, -76.93276],
        "y": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.x, df.y), 
        crs="EPSG:4326"
    )
    return gdf


@pytest.fixture
def nsi_sample_gdf_with_string_foundation():
    """
    Create a sample GeoDataFrame with NSI data using string foundation types (found_type instead of fndtype).
    """
    df = pd.DataFrame({
        "target_fid": ["NSI004", "NSI005", "NSI006"],
        "occtype": ["RES1", "RES2", "COM1"],
        "found_ht": [2.0, 3.5, 1.0],
        "found_type": ["S", "C", "I"],  # String codes: S=Slab, C=Crawl, I=Pile
        "num_story": [1, 2, 1],
        "sqft": [1800, 2400, 5000],
        "val_struct": [250000, 350000, 500000],
        "val_cont": [75000, 100000, 150000],
        "bldgtype": ["W", "M", "S"],  # W=Wood, M=Masonry, S=Steel
        "x": [-76.27738, -76.49555, -76.93276],
        "y": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.x, df.y), 
        crs="EPSG:4326"
    )
    return gdf


@pytest.fixture
def nsi_sample_gdf_missing_optional():
    """
    Create a sample GeoDataFrame with NSI data missing optional fields (occtype, found_ht, val_cont).
    """
    df = pd.DataFrame({
        "target_fid": ["NSI007", "NSI008", "NSI009"],
        "occtype": [None, "RES1", None],  # Some missing
        "found_ht": [2.0, None, None],  # Some missing
        "found_type": ["S", None, "I"],  # Some missing
        "num_story": [1, 2, 1],
        "sqft": [1800, 2400, 5000],
        "val_struct": [250000, 350000, 500000],
        "val_cont": [None, 100000, None],  # Some missing
        "bldgtype": ["W", None, None],  # Some missing
        "x": [-76.27738, -76.49555, -76.93276],
        "y": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.x, df.y), 
        crs="EPSG:4326"
    )
    return gdf


@pytest.fixture
def nsi_sample_gdf_missing_required():
    """
    Create a sample GeoDataFrame missing REQUIRED fields (num_story).
    """
    df = pd.DataFrame({
        "target_fid": ["NSI010", "NSI011", "NSI012"],
        "occtype": ["RES1", "RES1", "COM1"],
        "found_ht": [2.0, 3.5, 1.0],
        "found_type": ["S", "C", "I"],
        # "num_story": [1, 2, 1],  # MISSING REQUIRED FIELD
        "sqft": [1800, 2400, 5000],
        "val_struct": [250000, 350000, 500000],
        "val_cont": [75000, 100000, 150000],
        "bldgtype": ["W", "W", "C"],
        "x": [-76.27738, -76.49555, -76.93276],
        "y": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.x, df.y), 
        crs="EPSG:4326"
    )
    return gdf


@pytest.fixture
def nsi_sample_gdf_required_with_nans():
    """
    Create a sample GeoDataFrame with missing values in REQUIRED fields.
    """
    df = pd.DataFrame({
        "target_fid": ["NSI013", "NSI014", "NSI015"],
        "occtype": ["RES1", "RES1", "COM1"],
        "found_ht": [2.0, 3.5, 1.0],
        "found_type": ["S", "C", "I"],
        "num_story": [1, None, 1],  # Has NaN in required field
        "sqft": [1800, 2400, 5000],
        "val_struct": [250000, None, 500000],  # Has NaN in required field
        "val_cont": [75000, 100000, 150000],
        "bldgtype": ["W", "W", "C"],
        "x": [-76.27738, -76.49555, -76.93276],
        "y": [38.96829, 39.36650, 38.79571],
    })

    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.x, df.y), 
        crs="EPSG:4326"
    )
    return gdf


def test_load_valid_nsi_data(nsi_sample_gdf):
    """Test that NsiBuildings can be instantiated with NSI data."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Assert that the underlying GeoDataFrame has the expected records
    assert len(nb.gdf) == 3


def test_nsi_building_cost_mapping(nsi_sample_gdf):
    """Test that val_struct is correctly mapped to building_cost using the NSI defaults."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Access building_cost through the property
    costs = nb.building_cost
    
    # Should return values from val_struct column
    assert len(costs) == 3
    assert costs.iloc[0] == 250000
    assert costs.iloc[1] == 350000
    assert costs.iloc[2] == 500000


def test_nsi_occupancy_preprocessing(nsi_sample_gdf):
    """Test that occupancy types with suffixes are preprocessed correctly."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Occupancy types should have suffixes removed
    occ_types = nb.occupancy_type
    assert occ_types.iloc[0] == "RES1"
    assert occ_types.iloc[1] == "RES1"
    assert occ_types.iloc[2] == "COM1"


def test_nsi_foundation_type_preprocessing(nsi_sample_gdf):
    """Test that found_type is renamed to foundation_type."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Foundation types should be accessible via foundation_type property
    found_types = nb.foundation_type
    assert found_types.iloc[0] == "S"  # Slab
    assert found_types.iloc[1] == "C"  # Crawl
    assert found_types.iloc[2] == "I"  # Pile
    
    # Original found_type column should be dropped after preprocessing
    assert "found_type" not in nb.gdf.columns


def test_nsi_foundation_type_string(nsi_sample_gdf_with_string_foundation):
    """Test that string foundation types (found_type) are handled correctly."""
    nb = NsiBuildings(nsi_sample_gdf_with_string_foundation)
    
    # Foundation types should remain as-is when already strings
    found_types = nb.foundation_type
    assert found_types.iloc[0] == "S"
    assert found_types.iloc[1] == "C"
    assert found_types.iloc[2] == "I"


def test_nsi_field_mapping_visible(nsi_sample_gdf):
    """Test that we can see the field mapping based on NSI defaults."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Check that the mappings are as expected
    assert nb.fields.get_field_name("id") == "target_fid"
    assert nb.fields.get_field_name("occupancy_type") == "occtype"
    assert nb.fields.get_field_name("first_floor_height") == "found_ht"
    assert nb.fields.get_field_name("foundation_type") == "foundation_type"  # Preprocessed
    assert nb.fields.get_field_name("number_stories") == "num_story"
    assert nb.fields.get_field_name("area") == "sqft"
    assert nb.fields.get_field_name("building_cost") == "val_struct"
    assert nb.fields.get_field_name("content_cost") == "val_cont"
    assert nb.fields.get_field_name("general_building_type") == "bldgtype"


def test_nsi_with_user_overrides(nsi_sample_gdf):
    """Test that user overrides take precedence over NSI defaults."""
    # Add a custom cost column
    nsi_sample_gdf["custom_struct_cost"] = [300000, 400000, 600000]
    
    # User wants to use their custom column for building_cost
    user_overrides = {"building_cost": "custom_struct_cost"}
    
    nb = NsiBuildings(nsi_sample_gdf, overrides=user_overrides)
    
    # Should use the custom column, not val_struct
    costs = nb.building_cost
    assert costs.iloc[0] == 300000
    assert costs.iloc[1] == 400000
    assert costs.iloc[2] == 600000


def test_nsi_impute_missing_optional_fields(nsi_sample_gdf_missing_optional):
    """Test that optional fields with missing values are imputed correctly."""
    nb = NsiBuildings(nsi_sample_gdf_missing_optional)
    
    # Check that occupancy_type was imputed with default "RES1"
    occ_types = nb.occupancy_type
    assert not occ_types.isna().any()
    assert occ_types.iloc[0] == "RES1"  # Was None, should be imputed
    assert occ_types.iloc[1] == "RES1"  # Was already RES1
    assert occ_types.iloc[2] == "RES1"  # Was None, should be imputed
    
    # Check that foundation_type was imputed with default "S" (Slab)
    found_types = nb.foundation_type
    assert not found_types.isna().any()
    assert found_types.iloc[0] == "S"  # From found_type="S"
    assert found_types.iloc[1] == "S"  # Was None, should be imputed
    assert found_types.iloc[2] == "I"  # From found_type="I"


def test_nsi_missing_required_field(nsi_sample_gdf_missing_required):
    """Test that missing required fields raises an error."""
    with pytest.raises(ValueError, match="Required fields not found"):
        nb = NsiBuildings(nsi_sample_gdf_missing_required)


def test_nsi_required_fields_with_nans(nsi_sample_gdf_required_with_nans):
    """Test that having missing values in required fields raises an error."""
    with pytest.raises(ValueError, match="Required fields have missing values"):
        nb = NsiBuildings(nsi_sample_gdf_required_with_nans)


def test_nsi_all_fields_accessible(nsi_sample_gdf):
    """Test that all NSI fields can be accessed through properties."""
    nb = NsiBuildings(nsi_sample_gdf)
    
    # Test all mapped fields
    assert len(nb.id) == 3
    assert len(nb.occupancy_type) == 3
    assert len(nb.first_floor_height) == 3
    assert len(nb.foundation_type) == 3
    assert len(nb.number_stories) == 3
    assert len(nb.area) == 3
    assert len(nb.building_cost) == 3
    assert len(nb.content_cost) == 3


def test_nsi_content_value_imputation():
    """Test that missing content values are imputed based on occupancy type"""
    df = pd.DataFrame({
        "target_fid": ["1", "2", "3", "4"],
        "occtype": ["RES1", "COM1", "COM6", "IND1"],  # 50%, 100%, 150%, 150%
        "num_story": [1, 2, 3, 1],
        "sqft": [1500, 3000, 5000, 10000],
        "val_struct": [100000, 200000, 300000, 500000],
        "val_cont": [None, None, None, None],  # All missing
        "x": [-77.0, -77.1, -77.2, -77.3],
        "y": [38.0, 38.1, 38.2, 38.3],
    })
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y), crs="EPSG:4326")
    nb = NsiBuildings(gdf)
    
    # Expected content values based on occupancy type ratios
    assert nb.content_cost[0] == 50000    # RES1: 100000 * 0.50
    assert nb.content_cost[1] == 200000   # COM1: 200000 * 1.00
    assert nb.content_cost[2] == 450000   # COM6: 300000 * 1.50
    assert nb.content_cost[3] == 750000   # IND1: 500000 * 1.50


def test_nsi_content_value_partial_imputation():
    """Test that only missing content values are imputed, existing values preserved"""
    df = pd.DataFrame({
        "target_fid": ["1", "2", "3"],
        "occtype": ["RES1", "COM1", "COM6"],
        "num_story": [1, 2, 3],
        "sqft": [1500, 3000, 5000],
        "val_struct": [100000, 200000, 300000],
        "val_cont": [60000, None, 400000],  # Only middle one missing
        "x": [-77.0, -77.1, -77.2],
        "y": [38.0, 38.1, 38.2],
    })
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y), crs="EPSG:4326")
    nb = NsiBuildings(gdf)
    
    assert nb.content_cost[0] == 60000    # Preserved original value
    assert nb.content_cost[1] == 200000   # Imputed: COM1 = 200000 * 1.00
    assert nb.content_cost[2] == 400000   # Preserved original value
