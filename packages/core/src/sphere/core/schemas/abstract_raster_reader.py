import numpy as np
import geopandas as gpd
from abc import ABC, abstractmethod


class AbstractRasterReader(ABC):
    @property
    def data_source(self) -> str | None:
        """Returns the source identifier (e.g. file path) for this raster, or None if unknown."""
        return getattr(self, "_data_source", None)

    @data_source.setter
    def data_source(self, value) -> None:
        self._data_source = value

    @abstractmethod
    def get_value(self, lon: float, lat: float) -> float:
        """Returns flood depth at a given point; must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_value_vectorized(self, geometry: gpd.GeoSeries) -> np.ndarray:
        """Returns flood depth for multiple locations in a vectorized way; must be implemented by subclasses."""
        pass