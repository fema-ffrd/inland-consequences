"""Inland Consequences - Flood consequence modeling for inland and coastal scenarios.

This package provides tools for flood damage analysis, vulnerability assessment,
and loss aggregation for building inventories.
"""

from .inland_flood_analysis import InlandFloodAnalysis
from .inland_vulnerability import InlandFloodVulnerability
from .raster_collection import RasterCollection
from .results_aggregation import FloodResultsAggregator
from .nsi_buildings import NsiBuildings
from .milliman_buildings import MillimanBuildings

__all__ = [
    "InlandFloodAnalysis",
    "InlandFloodVulnerability",
    "RasterCollection",
    "FloodResultsAggregator",
    "NsiBuildings",
    "MillimanBuildings",
]


def main() -> None:
    print("Hello from inland_consequences package")
