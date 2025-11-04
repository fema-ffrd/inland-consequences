from typing import Dict, Optional
import geopandas as gpd

from sphere.core.schemas.buildings import Buildings


class MillimanBuildings(Buildings):
    """
    Placeholder subclass of the core Buildings class for Milliman-specific logic.

    This is intentionally minimal: it currently only subclasses the shared
    Buildings implementation and exists as a place to add Milliman-specific
    behavior later.
    """

    def __init__(self, gdf: gpd.GeoDataFrame, overrides: Optional[Dict[str, str]] = None):
        # Delegate initialization to the base Buildings class
        super().__init__(gdf, overrides)

    # Add Milliman-specific methods here in the future
