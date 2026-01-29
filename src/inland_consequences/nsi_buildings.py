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
            "foundation_type": "foundation_type",  # mapped after preprocessing
            "number_stories": "num_story",
            "area": "sqft",
            "building_cost": "val_struct",
            "content_cost": "val_cont",
            "general_building_type": "bldgtype",
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

    def _impute_optional_fields(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Impute missing values in NSI optional fields using appropriate strategies. Note that defaults
        must align with any preprocessing steps applied earlier.
        """
        # impute occupancy_type if missing
        if "occtype" in gdf.columns:
            gdf["occtype"] = gdf["occtype"].fillna("RES1")  # Default to RES1 if missing

        # impute general_building_type if missing
        if "bldgtype" in gdf.columns:
            gdf["bldgtype"] = gdf["bldgtype"].fillna("W")  # Default to WOOD if missing

        # impute foundation_type if missing
        if "foundation_type" in gdf.columns:
            gdf["foundation_type"] = gdf["foundation_type"].fillna("S")  # Default to Slab

        # impute first floor height (found_ht) if missing based on foundation_type
        if "found_ht" in gdf.columns and "foundation_type" in gdf.columns:
            found_ht_defaults = {
                "I": 8.0,  # Pile
                "P": 3.0,  # Pier, aligns with Shallow Foundation default
                "W": 3.0,  # Solid Wall, aligns with Shallow Foundation default
                "B": 2.0,  # Basement
                "C": 3.0,  # Crawl, aligns with Shallow Foundation default
                "F": 1.0,  # Fill, aligns with Slab default
                "S": 1.0,  # Slab
            }
            # Convert categorical to float before filling
            defaults = gdf["foundation_type"].map(found_ht_defaults).fillna(1.0).astype(float)
            gdf["found_ht"] = gdf["found_ht"].fillna(defaults)
        
        # impute content value (val_cont) if missing based on occupancy type
        # using lookup table from docs/inventory_methodology.md Table 3
        if "val_cont" in gdf.columns and "val_struct" in gdf.columns and "occtype" in gdf.columns:
            content_value_ratios = {
                "AGR1": 1.00,
                "COM1": 1.00,
                "COM10": 0.50,
                "COM2": 1.00,
                "COM3": 1.00,
                "COM4": 1.00,
                "COM5": 1.00,
                "COM6": 1.50,
                "COM7": 1.50,
                "COM8": 1.00,
                "COM9": 1.00,
                "EDU1": 1.00,
                "EDU2": 1.50,
                "GOV1": 1.00,
                "GOV2": 1.50,
                "IND1": 1.50,
                "IND2": 1.50,
                "IND3": 1.50,
                "IND4": 1.50,
                "IND5": 1.50,
                "IND6": 1.00,
                "REL1": 1.00,
                "RES1": 0.50,
                "RES2": 0.50,
                "RES3A": 0.50,
                "RES3B": 0.50,
                "RES3C": 0.50,
                "RES3D": 0.50,
                "RES3E": 0.50,
                "RES3F": 0.50,
                "RES4": 0.50,
                "RES5": 0.50,
                "RES6": 0.50,
            }
            # Calculate content value as percentage of building value based on occupancy
            content_ratio = gdf["occtype"].map(content_value_ratios).fillna(0.50)  # Default to 50% if unknown
            imputed_content = gdf["val_struct"] * content_ratio
            # Use mask to avoid FutureWarning about downcasting
            mask = gdf["val_cont"].isna()
            gdf.loc[mask, "val_cont"] = imputed_content[mask]
        
        return gdf

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
            # Only process non-null values to preserve NaN for imputation
            mask = gdf["occtype"].notna()
            gdf.loc[mask, "occtype"] = gdf.loc[mask, "occtype"].astype(str).str.split('-', n=1).str[0]
         
        # Pre-process the foundation type field
        # found_type contains string codes (S, C, I, etc.) - rename to foundation_type
        if "found_type" in gdf.columns and "foundation_type" not in gdf.columns:
            gdf["foundation_type"] = gdf["found_type"].astype("category")
            gdf = gdf.drop(columns=["found_type"])
        
        # Impute optional fields with default values if missing
        gdf = self._impute_optional_fields(gdf)

        return gdf
