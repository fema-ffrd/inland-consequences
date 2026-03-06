"""Meta distribution entry for niyamit-sphere.

This package exists so the distribution has a canonical import name
(`niyamit_sphere`) while the bundled `sphere` package is placed under
`src/sphere/` and will be included in the wheel.
"""

from .results_aggregation import FloodResultsAggregator

__all__ = ["FloodResultsAggregator"]


def main() -> None:
    print("Hello from niyamit_sphere meta package")
