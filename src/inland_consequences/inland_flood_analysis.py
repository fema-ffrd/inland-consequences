from typing import Dict, Any, Optional, Tuple, List
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction
from .raster_collection import RasterCollection
import inspect
import numpy as np
import pandas as pd

# Raster inputs are provided via a RasterCollection instance which
# enforces labeled rasters per return period (depth required, optional
# uncertainty, velocity, duration).


class InlandFloodAnalysis:
    """Vectorized inland flood analysis orchestrator.

    This class expects a raster_input mapping of return_period -> raster-like object
    where each raster implements get_value_vectorized(geometries) -> array-like depths.
    The buildings object must expose a pandas Geo/DataFrame at `buildings.gdf`
    and contain a column with monetary values (building_value_col).
    The vulnerability object must implement calculate_vulnerability(exposure_df)
    and return a DataFrame of damage ratios with the same shape as exposure_df.
    """

    def __init__(
        self,
        raster_collection: RasterCollection,
        buildings: Any,
        vulnerability: AbstractVulnerabilityFunction,
        calculate_aal: bool = True,
        aal_rate_limits: Optional[Tuple[float, float]] = None,
    ) -> None:
        # Must be a RasterCollection instance (validated by its constructor)
        if not isinstance(raster_collection, RasterCollection):
            raise TypeError("raster_collection must be a RasterCollection instance")
        self.raster_collection = raster_collection
        self.buildings = buildings
        self.vulnerability: AbstractVulnerabilityFunction = vulnerability
        self.calculate_aal = calculate_aal
        self.aal_rate_limits = aal_rate_limits

        # Since the vulnerability needs the buildings right now we need to think about how to choose them and apply to keep the buildings in sync.

        # Minimal validation
        if not hasattr(self.buildings, "gdf"):
            raise ValueError("buildings must have a .gdf attribute containing building rows")

    def _calculate_exposure(self) -> pd.DataFrame:
        """Vectorized sampling of all rasters for all building geometries.

        Returns:
            DataFrame: rows=buildings.index, cols=return_periods (int)
        """
        gdf = self.buildings.gdf
        geometries = gdf.geometry if "geometry" in gdf.columns else gdf.index.to_series()

        exposures: Dict[int, np.ndarray] = {}
        uncertainties: Dict[int, np.ndarray] = {}

        # Iterate deterministic sorted return periods
        for rp in self.raster_collection.return_periods():
            spec = self.raster_collection.get(rp)
            depth_raster = spec.get("depth")
            uncertainty_spec = spec.get("uncertainty")
            velocity_raster = spec.get("velocity")
            duration_raster = spec.get("duration")

            # Enforce that depth_raster is an AbstractRasterReader instance
            if not isinstance(depth_raster, AbstractRasterReader):
                raise ValueError(f"Depth raster for return period {rp} must be an AbstractRasterReader instance")

            mean_values = np.asarray(depth_raster.get_value_vectorized(geometries))
            if mean_values.shape[0] != len(gdf):
                raise ValueError(f"Raster for return period {rp} returned {mean_values.shape[0]} values but expected {len(gdf)}")

            # Determine uncertainty values
            if uncertainty_spec is None:
                uvals = np.zeros(len(gdf))
            elif isinstance(uncertainty_spec, AbstractRasterReader):
                uvals = np.asarray(uncertainty_spec.get_value_vectorized(geometries))
                if uvals.shape[0] != len(gdf):
                    raise ValueError(f"Uncertainty raster for return period {rp} returned {uvals.shape[0]} values but expected {len(gdf)}")
            elif isinstance(uncertainty_spec, (int, float)):
                uvals = np.full(len(gdf), float(uncertainty_spec))
            else:
                raise ValueError(f"Uncertainty for return period {rp} must be an AbstractRasterReader, numeric, or None")

            # Compute depth columns: mean, min, max
            mean_col = f"flood_depth_{rp}_mean"
            min_col = f"flood_depth_{rp}_min"
            max_col = f"flood_depth_{rp}_max"

            self.buildings.gdf[mean_col] = mean_values
            self.buildings.gdf[min_col] = mean_values - uvals
            self.buildings.gdf[max_col] = mean_values + uvals

            # Optionally sample and attach velocity/duration if provided
            # Always create velocity column: sample if raster provided, otherwise fill with NaN
            vel_col = f"flood_velocity_{rp}"
            if velocity_raster is not None:
                vel_vals = np.asarray(velocity_raster.get_value_vectorized(geometries))
                if vel_vals.shape[0] != len(gdf):
                    raise ValueError(f"Velocity raster for return period {rp} returned {vel_vals.shape[0]} values but expected {len(gdf)}")
                self.buildings.gdf[vel_col] = vel_vals
            else:
                # fill with NaN so downstream code can check for presence
                self.buildings.gdf[vel_col] = np.full(len(gdf), np.nan)

            # Always create duration column: sample if raster provided, otherwise fill with NaN
            dur_col = f"flood_duration_{rp}"
            if duration_raster is not None:
                dur_vals = np.asarray(duration_raster.get_value_vectorized(geometries))
                if dur_vals.shape[0] != len(gdf):
                    raise ValueError(f"Duration raster for return period {rp} returned {dur_vals.shape[0]} values but expected {len(gdf)}")
                self.buildings.gdf[dur_col] = dur_vals
            else:
                self.buildings.gdf[dur_col] = np.full(len(gdf), np.nan)

            exposures[rp] = mean_values
            uncertainties[rp] = uvals

        exposure_df = pd.DataFrame(exposures, index=gdf.index)
        uncertainty_df = pd.DataFrame(uncertainties, index=gdf.index)

        # store uncertainty dataframe for downstream usage
        self.exposure_uncertainty = uncertainty_df
        return exposure_df

    def _calculate_damage(self, exposure_df: pd.DataFrame):
        """Use the vulnerability component to vectorize damage ratio lookup and compute loss.

        Returns:
            loss_df (DataFrame): monetary loss per building (rows) per scenario (cols)
        """
        
        # Placeholder for the damage computations.  Right now SPHERE has this all on the buildings gdf but we might be able to separate it out
        # to determine how we want to represent the interim values and the final values.

        return

    def _calculate_vulnerability(self, exposure_df: pd.DataFrame):
        """Placeholder wrapper for vulnerability calculation.

        Current implementation simply forwards to the provided vulnerability object's
        calculate_vulnerability method. No additional logic is added here; this
        method exists so higher-level orchestration can call a single method.
        """
        # Basic pass-through to the vulnerability object. Consumers may replace
        # this with a more sophisticated, vectorized implementation later.
        self.vulnerability.apply_damage_percentages()
        
        # Attempt a simple call with only exposure. Vulnerability implementations
        # that accept uncertainty may ignore it for now.
        return

    def _calculate_metrics(self, loss_df: pd.DataFrame) -> float:
        """Aggregate losses and optionally compute AAL using trapezoidal integration.

        Assumes keys of raster_input are return periods (ints) and uses AEP = 1/return_period.
        """
        # Sum losses per scenario
        total_losses = loss_df.sum(axis=0)

        # Apply rate limits if present
        if self.aal_rate_limits is not None:
            low, high = self.aal_rate_limits
            total_losses = total_losses.clip(lower=low, upper=high)

        # Prepare arrays for integration: x = AEP, y = total loss
        rps = np.array(list(total_losses.index), dtype=float)
        aeps = 1.0 / rps
        # sort by AEP ascending (from rare to frequent?) we'll sort by AEP
        order = np.argsort(aeps)
        x = np.asarray(aeps[order], dtype=float)
        y = np.asarray(total_losses.values[order], dtype=float)

        # Integrate over AEP domain using trapezoidal rule
        aal = float(np.trapz(y, x))
        return aal

    def run(self) -> Dict[str, Any]:
        exposure_df = self._calculate_exposure()
        self._calculate_vulnerability(exposure_df)
        loss_df = self._calculate_damage(exposure_df)

        # Summarize scenario losses as list of tuples (return_period, total_loss)
        total_losses = loss_df.sum(axis=0)
        # Create scenario_losses as list of (return_period, total_loss)
        rps = [int(x) for x in total_losses.index]
        vals = [float(x) for x in total_losses.values]
        scenario_losses: List[Tuple[int, float]] = list(zip(rps, vals))

        result: Dict[str, Any] = {"scenario_losses": scenario_losses}

        if self.calculate_aal:
            aal = self._calculate_metrics(loss_df)
            result["AAL"] = aal

        return result
