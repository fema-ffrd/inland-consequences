from typing import Mapping, Dict, Any, Optional, List
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
import numpy as np
import pandas as pd


class RasterCollection:
    """Wrapper that validates and normalizes raster inputs by return period.

    The expected canonical form is a mapping:
      return_period (int) -> {
          "depth": AbstractRasterReader,            # required
          "uncertainty": AbstractRasterReader|float|None,  # optional
          "velocity": AbstractRasterReader|None,   # optional
          "duration": AbstractRasterReader|None,   # optional
      }

    To avoid ambiguity this class prefers labeled inputs. A bare
    AbstractRasterReader may be provided and will be treated as the
    depth raster for that return period. Tuples/lists are intentionally
    rejected to avoid order-dependent semantics.
    """

    def __init__(self, rp_map: Mapping[int, Any]):
        if not rp_map:
            raise ValueError("rp_map cannot be empty")

        self.rasters: Dict[int, Dict[str, Optional[Any]]] = {}

        for rp, spec in rp_map.items():
            # Accept a bare raster as depth for backwards convenience
            if isinstance(spec, AbstractRasterReader):
                depth = spec
                uncertainty = None
                velocity = None
                duration = None
            else:
                # Require a mapping with label keys for clarity
                if not isinstance(spec, Mapping):
                    raise TypeError(
                        f"Raster spec for return period {rp} must be an AbstractRasterReader or a mapping with labeled rasters"
                    )

                depth = spec.get("depth")
                uncertainty = spec.get("uncertainty")
                velocity = spec.get("velocity")
                duration = spec.get("duration")

            if not isinstance(depth, AbstractRasterReader):
                raise ValueError(f"Depth raster for return period {rp} must be an AbstractRasterReader")

            # Validate optional types
            if uncertainty is not None and not (
                isinstance(uncertainty, AbstractRasterReader) or isinstance(uncertainty, (int, float))
            ):
                raise ValueError(
                    f"Uncertainty for return period {rp} must be an AbstractRasterReader, numeric, or None"
                )

            for name, val in (("velocity", velocity), ("duration", duration)):
                if val is not None and not isinstance(val, AbstractRasterReader):
                    raise ValueError(f"{name} for return period {rp} must be an AbstractRasterReader or None")

            self.rasters[int(rp)] = {
                "depth": depth,
                "uncertainty": uncertainty,
                "velocity": velocity,
                "duration": duration,
            }

        # Validate alignment: if any optional raster type is provided for some rps,
        # require it to be provided for all return periods to prevent mismatches.
        rps = set(self.rasters.keys())
        for label in ("velocity", "duration"):
            present = {rp for rp, d in self.rasters.items() if d.get(label) is not None}
            if present and present != rps:
                missing = sorted(rps - present)
                raise ValueError(
                    f"Inconsistent coverage for '{label}' rasters. Missing for RPs: {missing}."
                )

    def return_periods(self) -> List[int]:
        return sorted(self.rasters.keys())

    def get(self, rp: int) -> Dict[str, Optional[Any]]:
        return self.rasters[int(rp)]

    def items(self):
        return list(self.rasters.items())

    def sample_for_rp(self, rp: int, geometries) -> Dict[str, pd.Series]:
        """Sample depth/uncertainty/velocity/duration for a single return period.

        Returns a dict of pandas.Series with keys: 'depth', 'uncertainty', 'velocity', 'duration'.
        If an optional raster (velocity/duration) is not provided for the rp, the
        corresponding Series will be filled with NaN values of the appropriate length.

        Parameters:
        - rp: return period to sample
        - geometries: iterable of geometries to pass to raster.get_value_vectorized
                      (cannot be None)
        """
        if geometries is None:
            raise ValueError("geometries must be provided and cannot be None")

        spec = self.get(rp)
        idx = pd.Index(range(len(geometries)))
        geom_arg = geometries

        out: Dict[str, pd.Series] = {}

        # depth (required)
        depth = spec.get("depth")
        depth_vals = np.asarray(depth.get_value_vectorized(geom_arg))
        out["depth"] = pd.Series(depth_vals, index=idx)

        # uncertainty
        uncertainty = spec.get("uncertainty")
        if uncertainty is None:
            uvals = np.zeros(len(idx))
        elif isinstance(uncertainty, AbstractRasterReader):
            uvals = np.asarray(uncertainty.get_value_vectorized(geom_arg))
        else:
            uvals = np.full(len(idx), float(uncertainty))
        out["uncertainty"] = pd.Series(uvals, index=idx)

        # optional rasters: velocity, duration
        for name in ("velocity", "duration"):
            r = spec.get(name)
            if r is None:
                out[name] = pd.Series([np.nan] * len(idx), index=idx)
            else:
                vals = np.asarray(r.get_value_vectorized(geom_arg))
                out[name] = pd.Series(vals, index=idx)

        return out
