from typing import Dict, Optional, List
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd

from sphere.core.schemas.buildings import Buildings


class NsiBuildings(Buildings):
    """
    NSI (National Structure Inventory) specific subclass with field name overrides.
    
    This class defines NSI-specific field aliases that map their column names
    to the standard Buildings fields, leveraging the existing alias system.
    Includes preprocessing for occupancy and foundation types.
    """
    
    # Class-level schema path
    SCHEMA_PATH = Path(__file__).parent.parent.parent / "docs" / "schemas" / "nsi_schema.json"

    def __init__(self, gdf: gpd.GeoDataFrame, overrides: Optional[Dict[str, str]] = None):
        """
        Initialize NsiBuildings with NSI-specific field aliases.
        
        Args:
            gdf: GeoDataFrame containing NSI building data
            overrides: Optional user overrides that take precedence over NSI defaults
        """
        
        # Define NSI-specific field name mappings (keys = target fields, values = NSI fields)
        nsi_overrides = {
            "id": "target_fid",
            "occupancy_type": "occtype",
            "first_floor_height": "found_ht",
            "foundation_type": "fndtype",  # mapped after preprocessing
            "number_stories": "num_story",
            "area": "sqft",
            "building_cost": "val_struct",
            "content_cost": "val_cont",
        }
        
        # Merge with user overrides (user overrides take precedence)
        if overrides is None:
            final_overrides = nsi_overrides
        else:
            final_overrides = {**nsi_overrides, **overrides}

        # Preprocess the GeoDataFrame (occupancy and foundation types)
        gdf = self._preprocess_gdf(gdf)

        # Ensure required fields are present
        self._ensure_required_fields(gdf, final_overrides)

        # Ensure required fields have no missing values
        self._ensure_required_fields_complete(gdf, final_overrides)
        
        # Delegate to base Buildings class with NSI overrides
        super().__init__(gdf, final_overrides)
    
    @classmethod
    def _load_required_fields_from_schema(cls) -> List[str]:
        """
        Load required field names from the NSI schema JSON file.
        
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
        required_fields = self._load_required_fields_from_schema()
        
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
        required_fields = self._load_required_fields_from_schema()
        
        missing_value_fields = []
        for field in required_fields:
            col_name = overrides.get(field, field)
            if col_name in gdf.columns:
                if gdf[col_name].isna().any():
                    missing_value_fields.append(field)
        
        if missing_value_fields:
            raise ValueError(f"Required fields have missing values in GeoDataFrame: {missing_value_fields}")

    def _preprocess_gdf(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Pre-process the GeoDataFrame by cleaning occupancy and foundation types.
        
        Args:
            gdf: GeoDataFrame to preprocess
            
        Returns:
            Preprocessed GeoDataFrame
        """
        # Pre-process the occupancy type field to remove content after dash
        if "occtype" in gdf.columns:
            gdf["occtype"] = gdf["occtype"].astype(str)
            gdf["occtype"] = gdf["occtype"].str.split('-', n=1).str[0]
         
        # Pre-process the foundation type field to map numeric values to string codes
        if "fndtype" in gdf.columns and "foundation_type" not in gdf.columns:
            foundation_type_map = {
                1: "I",  # Pile
                2: "P",  # Pier
                3: "W",  # Solid Wall
                4: "B",  # Basement
                5: "C",  # Crawl
                6: "F",  # Fill
                7: "S",  # Slab
            }
            
            gdf["foundation_type"] = pd.to_numeric(gdf["fndtype"], errors='coerce') \
                                           .map(foundation_type_map) \
                                           .astype("category")

        return gdf
