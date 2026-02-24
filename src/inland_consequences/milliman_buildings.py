from typing import Dict, Optional, List
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd

from sphere.core.schemas.buildings import Buildings


class MillimanBuildings(Buildings):
    """
    Milliman-specific subclass with field name overrides for Milliman data formats.
    
    This class defines Milliman-specific field aliases that map their column names
    to the standard Buildings fields, leveraging the existing alias system.
    """
    
    # Class-level schema path
    SCHEMA_PATH = Path(__file__).parent.parent.parent / "docs" / "schemas" / "milliman_schema.json"
    
    # Fields that are imputed/generated and also required
    IMPUTED_REQUIRED_FIELDS = ["occupancy_type", "area"]

    def __init__(self, gdf: gpd.GeoDataFrame, overrides: Optional[Dict[str, str]] = None):
        """
        Initialize MillimanBuildings with Milliman-specific field aliases.
        
        Args:
            gdf: GeoDataFrame containing Milliman building data
            overrides: Optional user overrides that take precedence over Milliman defaults
        """
        
        # Define Milliman-specific field name mappings (keys = target fields, values = Milliman fields) from sample data
        milliman_overrides = {
            "id": "location",
            "building_cost": "BLDG_VALUE",
            "content_cost": "CNT_VALUE",
            "general_building_type": "general_building_type",  # created in preprocessing from CONSTR_CODE
            "foundation_type": "foundation_type",  # created in preprocessing from FoundationType
            "number_stories": "NUM_STORIES",
            "first_floor_height": "FIRST_FLOOR_ELEV",
        }
        
        # Merge with user overrides (user overrides take precedence during unpacking)
        if overrides is None:
            final_overrides = milliman_overrides
        else:
            final_overrides = {**milliman_overrides, **overrides}

        # Pre-process the GeoDataFrame (foundation and construction type conversion, imputation)
        # This creates the standard 'foundation_type' and 'general_building_type' columns
        gdf = self._preprocess_gdf(gdf)

        # Ensure required fields are present
        self._ensure_required_fields(gdf, final_overrides)

        # Ensure required fields have no missing values
        self._ensure_required_fields_complete(gdf, final_overrides)
        
        # Delegate to base Buildings class with Milliman overrides
        super().__init__(gdf, final_overrides)
    
    def _preprocess_gdf(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Pre-process the GeoDataFrame by mapping numeric foundation and construction types to string codes."""
        # Pre-process the foundation type field to map numeric values to string codes
        # Based on milliman_schema.json: 2=basement; 4=crawlspace; 6=pier; 7=fill or wall; 8=slab; 9=pile
        # This will match the approach used in the NSI buildings preprocessing
        if "FoundationType" in gdf.columns and "foundation_type" not in gdf.columns:
            foundation_type_map = {
                2: "BASE",  # Basement
                4: "SHAL",  # Crawlspace
                6: "SHAL",  # Pier
                7: "SLAB",  # Fill or wall (Wall)
                8: "SLAB",  # Slab
                9: "PILE",  # Pile
            }
            
            # Using pandas categories can be more memory efficient for large datasets
            gdf["foundation_type"] = pd.to_numeric(gdf["FoundationType"], errors='coerce') \
                                           .map(foundation_type_map) \
                                           .astype("category")
            
            # Drop the original column since we've converted it
            gdf = gdf.drop(columns=["FoundationType"])
        
        # Pre-process the construction type field to map numeric values to string codes
        # Based on milliman_schema.json: 1=Wood; 2=Masonry
        if "CONSTR_CODE" in gdf.columns and "general_building_type" not in gdf.columns:
            construction_type_map = {
                1: "W",  # Wood
                2: "M",  # Masonry
            }
            
            # Using pandas categories can be more memory efficient for large datasets
            gdf["general_building_type"] = pd.to_numeric(gdf["CONSTR_CODE"], errors='coerce') \
                                                  .map(construction_type_map) \
                                                  .astype("category")
            
            # Drop the original column since we've converted it
            gdf = gdf.drop(columns=["CONSTR_CODE"])
        
        # Impute optional fields with default values if missing
        gdf = self._impute_optional_fields(gdf)
        
        return gdf
    
    @classmethod
    def _load_required_fields_from_schema(cls) -> List[str]:
        """
        Load required field names from the Milliman schema JSON file.
        
        Returns:
            List of required target field names
        """
        if not cls.SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found at {cls.SCHEMA_PATH}")
        
        with open(cls.SCHEMA_PATH, 'r') as f:
            schema = json.load(f)
        
        required_fields = []
        for field_name, field_spec in schema.get("default fields", {}).items():
            if field_spec.get("required", False):
                target_field = field_spec.get("default target field")
                if target_field:
                    required_fields.append(target_field)
        
        return required_fields
    
    def _ensure_required_fields(self, gdf: gpd.GeoDataFrame, overrides: dict) -> None:
        """
        Ensure that all required fields are present in the GeoDataFrame or overrides.
        
        Args:
            gdf: GeoDataFrame to check
            overrides: Dictionary of field name overrides
        """
        # Load required fields from schema (single source of truth)
        required_fields = self._load_required_fields_from_schema()
        
        # Add imputed fields that are also required
        required_fields.extend(self.IMPUTED_REQUIRED_FIELDS)
        
        missing_fields = []
        for field in required_fields:
            col_name = overrides.get(field, field)
            if col_name not in gdf.columns and field not in overrides.values():
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Required fields not found in GeoDataFrame or overrides: {missing_fields}")

    def _ensure_required_fields_complete(self, gdf: gpd.GeoDataFrame, overrides: dict) -> None:
        """
        Ensure that all required fields have no missing values in the GeoDataFrame.
        
        Args:
            gdf: GeoDataFrame to check
            overrides: Dictionary of field name overrides
        """
        # Load required fields from schema (single source of truth)
        required_fields = self._load_required_fields_from_schema()
        
        # Add imputed fields that are also required
        required_fields.extend(self.IMPUTED_REQUIRED_FIELDS)
        
        missing_value_fields = []

        for field in required_fields:
            col_name = overrides.get(field, field)
            if col_name in gdf.columns:
                if gdf[col_name].isna().any():
                    missing_value_fields.append(field)
        
        if missing_value_fields:
            raise ValueError(f"Required fields have missing values in GeoDataFrame: {missing_value_fields}")

    def _impute_optional_fields(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Impute missing values in Milliman optional fields using appropriate strategies.
        Also creates fields that don't exist in Milliman source data but are required.
        """
        # Create fields that don't exist in Milliman data (IMPUTED_REQUIRED_FIELDS)
        if "occupancy_type" not in gdf.columns:
            gdf["occupancy_type"] = "RES1"  # Default occupancy type
        else:
            gdf["occupancy_type"] = gdf["occupancy_type"].fillna("RES1")
        
        if "area" not in gdf.columns:
            gdf["area"] = 1800  # Default RES1 square footage
        else:
            gdf["area"] = gdf["area"].fillna(1800)
        
        # Impute optional fields that exist in schema but may have missing values
        # foundation_type and general_building_type are created during preprocessing
        if "foundation_type" in gdf.columns:
            gdf["foundation_type"] = gdf["foundation_type"].fillna("SLAB")  # Default to Slab (4-letter code)
        
        if "general_building_type" in gdf.columns:
            gdf["general_building_type"] = gdf["general_building_type"].fillna("W")  # Default to Wood
        
        return gdf
