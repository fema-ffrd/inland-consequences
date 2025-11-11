import numpy as np
import pandas as pd
import pytest

from inland_consequences.inland_flood_analysis import InlandFloodAnalysis
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader


# --- Mocks used across tests -------------------------------------------------
class MockRaster(AbstractRasterReader):
    """Simple raster-like object for tests.

    It exposes get_value_vectorized(geometries) and returns a fixed array of
    values (ignores geometries).
    """

    def __init__(self, values):
        self.values = np.asarray(values)

    def get_value_vectorized(self, geometries):
        return np.asarray(self.values)

    def get_value(self, lon: float, lat: float) -> float:
        # Return the first value for single-point queries in tests.
        return float(self.values[0])


class MockBuildings:
    """Tiny buildings container exposing a minimal .gdf expected by the analysis."""

    def __init__(self, values):
        # create a simple DataFrame to act like a GeoDataFrame
        self.gdf = pd.DataFrame({"geometry": [None] * len(values), "value": values})


# Note: some tests in this file use a very small vulnerability helper that
# multiplies exposures by a constant to produce damage ratios.
class MockVulnerability:
    def __init__(self, multiplier=0.1):
        self.multiplier = multiplier
        self.called_with = None

    def calculate_vulnerability(self, exposure_df: pd.DataFrame) -> pd.DataFrame:
        # record call
        self.called_with = exposure_df.copy()
        # Return a damage ratio simply as exposure * multiplier (vectorized)
        return exposure_df * self.multiplier


def test_calculate_exposure():
    """Basic exposure calculation with no uncertainty provided.

    Verifies that returned DataFrame has the expected columns and values and
    that the analysis records zero uncertainty in that case.
    """
    buildings = MockBuildings([100, 200, 300])
    raster_input = {
        10: MockRaster([1.0, 2.0, 3.0]),
        100: MockRaster([0.5, 1.5, 2.5]),
    }
    vuln = MockVulnerability()

    analysis = InlandFloodAnalysis(raster_input, buildings, vuln, calculate_aal=False)
    exposure = analysis._calculate_exposure()

    # columns are the return periods
    assert list(exposure.columns) == [10, 100]
    assert exposure.shape == (3, 2)
    assert exposure.loc[0, 10] == pytest.approx(1.0)
    assert exposure.loc[2, 100] == pytest.approx(2.5)

    # since no uncertainty was specified, the stored uncertainty dataframe
    # should be all zeros and min==mean==max
    assert hasattr(analysis, "exposure_uncertainty")
    assert analysis.exposure_uncertainty.shape == exposure.shape
    assert (analysis.exposure_uncertainty.values == 0).all()
    assert np.allclose(buildings.gdf["flood_depth_10_min"].values, buildings.gdf["flood_depth_10_mean"].values)


def test_calculate_exposure_with_numeric_uncertainty():
    """When a numeric uncertainty is provided it should be applied to all
    buildings (mean +/- uncertainty) and recorded in exposure_uncertainty."""

    buildings = MockBuildings([10, 20])
    # Provide a numeric uncertainty (0.2) for RP=5
    raster_input = {5: (MockRaster([2.0, 3.0]), 0.2)}
    vuln = MockVulnerability()

    analysis = InlandFloodAnalysis(raster_input, buildings, vuln, calculate_aal=False)
    exposure = analysis._calculate_exposure()

    # exposure values come from depth raster
    assert exposure.loc[0, 5] == pytest.approx(2.0)
    assert exposure.loc[1, 5] == pytest.approx(3.0)

    # uncertainty should be recorded and equal to the numeric value for each row
    assert np.allclose(analysis.exposure_uncertainty[5].values, np.array([0.2, 0.2]))

    # check min/max columns on buildings.gdf
    assert np.allclose(buildings.gdf["flood_depth_5_min"].values, np.array([1.8, 2.8]))
    assert np.allclose(buildings.gdf["flood_depth_5_max"].values, np.array([2.2, 3.2]))


def test_calculate_exposure_with_raster_uncertainty_between_0_and_1():
    """Support uncertainty specified as a raster-like object. Use values
    between 0.0 and 1.0 to ensure fractional uncertainties are handled."""

    buildings = MockBuildings([1, 1, 1])
    depth_raster = MockRaster([0.2, 0.4, 0.6])
    uncertainty_raster = MockRaster([0.05, 0.1, 0.2])

    # Provide (depth, uncertainty) tuple for RP=20
    raster_input = {20: (depth_raster, uncertainty_raster)}
    vuln = MockVulnerability()

    analysis = InlandFloodAnalysis(raster_input, buildings, vuln, calculate_aal=False)
    exposure = analysis._calculate_exposure()

    # check exposure matches depth raster
    assert np.allclose(exposure[20].values, np.array([0.2, 0.4, 0.6]))

    # uncertainty stored should match the uncertainty raster values
    assert np.allclose(analysis.exposure_uncertainty[20].values, np.array([0.05, 0.1, 0.2]))

    # min/max should be mean +/- uncertainty
    assert np.allclose(buildings.gdf["flood_depth_20_min"].values, np.array([0.15, 0.3, 0.4]))
    assert np.allclose(buildings.gdf["flood_depth_20_max"].values, np.array([0.25, 0.5, 0.8]))

