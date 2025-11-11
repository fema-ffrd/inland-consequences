import numpy as np
import pandas as pd
import pytest

from inland_consequences.raster_collection import RasterCollection
from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader


class MockRaster(AbstractRasterReader):
    def __init__(self, values):
        self.values = np.asarray(values)

    def get_value_vectorized(self, geometries):
        return np.asarray(self.values)

    def get_value(self, lon: float, lat: float) -> float:
        return float(self.values[0])


class MockBuildings:
    def __init__(self, n_rows):
        # create a minimal DataFrame that mimics a GeoDataFrame
        self.gdf = pd.DataFrame({"geometry": [None] * n_rows})


def test_rastercollection_requires_full_coverage_for_velocity():
    """If velocity provided for only some RPs, constructor should raise."""
    rc_map = {
        10: {"depth": MockRaster([1.0, 2.0]), "velocity": MockRaster([0.1, 0.2])},
        100: {"depth": MockRaster([0.5, 1.5])},
    }

    with pytest.raises(ValueError, match="Inconsistent coverage.*'velocity'"):
        RasterCollection(rc_map)


def test_get_depth_raster_and_sampling():
    """Ensure RasterCollection.get returns an AbstractRasterReader for depth and it samples correctly."""
    rc_map = {5: {"depth": MockRaster([2.0, 3.0]), "uncertainty": 0.2}}
    rc = RasterCollection(rc_map)

    spec = rc.get(5)
    assert isinstance(spec["depth"], AbstractRasterReader)

    sampled = np.asarray(spec["depth"].get_value_vectorized(None))
    assert np.allclose(sampled, np.array([2.0, 3.0]))


def test_missing_optional_raster_filled_with_nan():
    """If velocity/duration rasters are not supplied, the exposure step should
    still create the columns and fill them with NaN so downstream code sees
    a consistent schema."""
    buildings = MockBuildings(2)

    rc_map = {
        10: {"depth": MockRaster([1.0, 2.0])},
        100: {"depth": MockRaster([0.5, 1.5])},
    }
    rc = RasterCollection(rc_map)

    class DummyVuln:
        def apply_damage_percentages(self):
            return

    # Sample directly from RasterCollection rather than using InlandFloodAnalysis
    sampled_10 = rc.sample_for_rp(10, geometries=list(range(2)))
    sampled_100 = rc.sample_for_rp(100, geometries=list(range(2)))

    # velocity/duration series should exist and be all NaN
    assert "velocity" in sampled_10
    assert "duration" in sampled_100
    assert sampled_10["velocity"].isna().all()
    assert sampled_100["duration"].isna().all()

