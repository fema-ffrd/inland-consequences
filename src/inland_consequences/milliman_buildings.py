from typing import Dict, Optional, List
import json
from pathlib import Path
import geopandas as gpd

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
            "number_stories": "NUM_STORIE",
            "foundation_type": "foundation",
            "first_floor_height": "FIRST_FLOO",
            # Add other Milliman-specific field names as needed
            # TODO: "target_field_DEMft?": "DEMft",
            # TODO: "target_field_basement_finish_type?": "BasementFi"
        }
        
        # Merge with user overrides (user overrides take precedence during unpacking)
        if overrides is None:
            final_overrides = milliman_overrides
        else:
            final_overrides = {**milliman_overrides, **overrides}

        # impute missing Milliman values based on defaults
        gdf = self._impute_missing_milliman_values(gdf, final_overrides)

        # Ensure required fields are present
        self._ensure_required_fields(gdf, final_overrides)

        # Ensure required fields have no missing values
        self._ensure_required_fields_complete(gdf, final_overrides)
        
        # Delegate to base Buildings class with Milliman overrides
        super().__init__(gdf, final_overrides)
    
    @classmethod
    def _load_required_fields_from_schema(cls) -> List[str]:
        """
        Load required field names from the Milliman schema JSON file.
        
        Returns:
            List of required field names (source column names from Milliman data)
        """
        if not cls.SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found at {cls.SCHEMA_PATH}")
        
        with open(cls.SCHEMA_PATH, 'r') as f:
            schema = json.load(f)
        
        required_fields = []
        for field_name, field_spec in schema.get("default fields", {}).items():
            if field_spec.get("required", False):
                required_fields.append(field_name)
        
        return required_fields
    
    def _ensure_required_fields(self, gdf: gpd.GeoDataFrame, overrides: dict) -> None:
        """
        Ensure that all required fields are present in the GeoDataFrame or provided in
        overrides dictionary as keys.
        
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
            if field not in gdf.columns and field not in overrides.keys():
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Required input fields not found in GeoDataFrame or overrides: {missing_fields}")

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
            raise ValueError(f"Required input fields have missing values in GeoDataFrame: {missing_value_fields}")

    def _impute_missing_milliman_values(self, gdf: gpd.GeoDataFrame, overrides: dict) -> gpd.GeoDataFrame:
        """
        Impute missing values in Milliman-specific fields based on known defaults.
        Generate fields that don't exist in Milliman data.
        
        Args:
            gdf: GeoDataFrame to process
            overrides: Dictionary of field name overrides
        Returns:
            GeoDataFrame with imputed values
        """
        # Define default values for Milliman fields (uniform defaults)
        milliman_defaults = {
            "occupancy_type": "RES1",  # default occupancy type
            "area": 1800  # default RES1 square footage
        }

        # Generate or impute fields using defaults
        for field_name, default_value in milliman_defaults.items():
            col_name = overrides.get(field_name, field_name)
            
            # If column doesn't exist, create it with default value
            if col_name not in gdf.columns:
                gdf[col_name] = default_value
            else:
                # If column exists but has missing values, fill them
                gdf[col_name] = gdf[col_name].fillna(default_value)

        return gdf
