"""pytest conftest to ensure the project's src/ directory is on sys.path

This allows tests to import the package as 'inland_consequences' when the
project uses the src/ layout without requiring an editable install.
"""
import os
import sys


def _add_src_to_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    if os.path.isdir(src_path) and src_path not in sys.path:
        sys.path.insert(0, src_path)


_add_src_to_path()
import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
from sphere.core.schemas.buildings import Buildings


def create_sample_for_rp_mock(return_periods_data):
    """
    Creates a sample_for_rp side_effect function for mocking RasterCollection.
    
    Args:
        return_periods_data: dict mapping return_period -> dict with keys:
            - depth: list of depth values
            - uncertainty: list of uncertainty values (defaults to 0.0 if not provided)
            - velocity: list of velocity values (defaults to NaN if not provided)
            - duration: list of duration values (defaults to NaN if not provided)
    
    Returns:
        A function suitable for use as MagicMock.side_effect for sample_for_rp
    
    Example:
        data = {
            100: {"depth": [1.0, 2.0, 3.0]},
            500: {"depth": [1.5, 2.5, 3.5], "uncertainty": [0.5, 0.5, 0.5]}
        }
        mock_collection.sample_for_rp.side_effect = create_sample_for_rp_mock(data)
    """
    def mock_sample_for_rp(rp, geometries):
        n = len(geometries)
        idx = pd.Index(range(n))
        
        if rp in return_periods_data:
            rp_data = return_periods_data[rp]
            depth_vals = rp_data.get("depth", [0.0] * n)[:n]
            unc_vals = rp_data.get("uncertainty", [0.0] * n)[:n]
            vel_vals = rp_data.get("velocity", [np.nan] * n)[:n]
            dur_vals = rp_data.get("duration", [np.nan] * n)[:n]
        else:
            depth_vals = [0.0] * n
            unc_vals = [0.0] * n
            vel_vals = [np.nan] * n
            dur_vals = [np.nan] * n
        
        return {
            "depth": pd.Series(depth_vals, index=idx),
            "uncertainty": pd.Series(unc_vals, index=idx),
            "velocity": pd.Series(vel_vals, index=idx),
            "duration": pd.Series(dur_vals, index=idx),
        }
    
    return mock_sample_for_rp


class DummyBuildingPoints(Buildings):
    def __init__(self, gdf: gpd.GeoDataFrame):
        overrides = {
            "id": "Id",
            "occupancy_type": "OccupancyType",
            # All of these below here should be the defaults but if that changes overriding
            "first_floor_height": "FirstFloorHt",
            "foundation_type": "FoundationType",
            "number_stories": "NumStories",
            "area": "Area",
            "building_cost": "Cost",
            "content_cost": "ContentCostUSD",
            "inventory_cost": "InventoryCostUSD",
            # These can be added if missing below this line
            "flood_depth": "Depth_Grid",
            "depth_in_structure": "Depth_in_Struc",
            "bddf_id": "BDDF_ID",
            "building_damage_percent": "BuildingDamagePct",
            "building_loss": "BldgLossUSD",
            "cddf_id": "CDDF_ID",
            "content_damage_percent": "ContentDamagePct",
            "content_loss": "ContentLossUSD",
            "iddf_id": "IDDF_ID",
            "inventory_damage_percent": "InventoryDamagePct",
            "inventory_loss": "InventoryLossUSD",
            "debris_finish": "DebrisFinish",
            "debris_foundation": "DebrisFoundation",
            "debris_structure": "DebrisStructure",
            "debris_total": "DebrisTotal",
            "restoration_minimum": "Restor_Days_Min",
            "restoration_maximum": "Restor_Days_Max",
        }
        
        super().__init__(gdf, overrides)
        self._gdf = gdf

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        return self._gdf


@pytest.fixture
def small_udf_buildings():
    data = [
        {
            "Id": 1,
            "HNL_UDF_EQ": "RM1M",
            "OccupancyType": "RES3E",
            "Cost": 2254898,
            "NumStories": 7,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 11040,
            "BDDF_ID": 204,
            "CDDF_ID": 81,
            "YEARBUILT": 1974,
            "Tract": 15003000106,
            "Latitude": 21.29,
            "Longitude": -157.72,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R3E5N",
            "ContentCostUSD": 1127449,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 31.0,
            "BldgLossUSD": 699018.38,
            "ContDmgPct": 41.0,
            "ContentLossUSD": 462254.09,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES3ENBSG4",
            "Debris_Fin": 75.072,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 75.072,
            "Restor_Days_Min": 360,
            "Restor_Days_Max": 540,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53611,
            "HNL_UDF_EQ": "PC1",
            "OccupancyType": "IND2",
            "Cost": 1484865,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 11724,
            "BDDF_ID": 559,
            "CDDF_ID": 384,
            "YEARBUILT": 1988,
            "Tract": 15003010000,
            "Latitude": 21.59,
            "Longitude": -158.1,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "I2LN",
            "ContentCostUSD": 2227298,
            "InventoryCostUSD": 105984.96,
            "BldgDmgPct": 26.0,
            "BldgLossUSD": 386064.9,
            "ContDmgPct": 52.0,
            "ContentLossUSD": 1158194.96,
            "IDDF_ID": 81,
            "InvDmgPct": 63.0,
            "InventoryLossUSD": 66770.5248,
            "DebrisID": "IND2NBSG4",
            "Debris_Fin": 8.2068,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 8.2068,
            "Restor_Days_Min": 30,
            "Restor_Days_Max": 150,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53618,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 597165,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 3438,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1961,
            "Tract": 15003010000,
            "Latitude": 21.56,
            "Longitude": -158.11,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 298582,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 274695.9,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 119432.8,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 23.3784,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 23.3784,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53617,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 628604,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 3619,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1963,
            "Tract": 15003010000,
            "Latitude": 21.56,
            "Longitude": -158.11,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 314302,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 289157.84,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 125720.8,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 24.6092,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 24.6092,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53616,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 777982,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 4479,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1971,
            "Tract": 15003010000,
            "Latitude": 21.56,
            "Longitude": -158.11,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 388991,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 357871.72000000003,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 155596.4,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 30.4572,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 30.4572,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53615,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 366324,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 2109,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1955,
            "Tract": 15003010000,
            "Latitude": 21.59,
            "Longitude": -158.1,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 183162,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 168509.04,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 73264.8,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 14.3412,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 14.3412,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53614,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 239526,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 1379,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1941,
            "Tract": 15003010000,
            "Latitude": 21.62,
            "Longitude": -158.09,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 119763,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 110181.96,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 47905.2,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 9.377199999999998,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 9.377199999999998,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53613,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 285208,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 1642,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1930,
            "Tract": 15003010000,
            "Latitude": 21.62,
            "Longitude": -158.08,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 142604,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 131195.68,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 57041.600000000006,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 11.1656,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 11.1656,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
        {
            "Id": 53612,
            "HNL_UDF_EQ": "W1",
            "OccupancyType": "RES1",
            "Cost": 61141,
            "NumStories": 1,
            "FoundationType": 7,
            "FirstFloorHt": 1,
            "Area": 352,
            "BDDF_ID": 213,
            "CDDF_ID": 29,
            "YEARBUILT": 1949,
            "Tract": 15003010000,
            "Latitude": 21.62,
            "Longitude": -158.08,
            "Depth_Grid": 6.0,
            "Depth_in_Struc": 5.0,
            "flExp": 1,
            "SOID": "R11N",
            "ContentCostUSD": 30570,
            "InventoryCostUSD": 0.0,
            "BldgDmgPct": 46.0,
            "BldgLossUSD": 28124.86,
            "ContDmgPct": 40.0,
            "ContentLossUSD": 12228.0,
            "IDDF_ID": 0,
            "InvDmgPct": 0.0,
            "InventoryLossUSD": 0.0,
            "DebrisID": "RES1NBSG4",
            "Debris_Fin": 2.3936,
            "Debris_Struc": 0.0,
            "Debris_Found": 0.0,
            "Debris_Tot": 2.3936,
            "Restor_Days_Min": 270,
            "Restor_Days_Max": 450,
            "GridName": "Honolulu_6_Foot2",
        },
    ]
    df = pd.DataFrame(data)
    # Vectorized loading of the geodataframe from x y columns
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
    )
    return DummyBuildingPoints(gdf=gdf)
