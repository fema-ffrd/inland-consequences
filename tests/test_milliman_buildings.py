import pandas as pd
import geopandas as gpd

from inland_consequences.milliman_buildings import MillimanBuildings


def test_milliman_buildings_gdf_has_record():
    # Create a minimal GeoDataFrame with one building record
    df = pd.DataFrame({
        "building_id": [1],
        "occupancy_type": ["RES1"],
        "first_floor_height": [1.0],
        "foundation_type": [7],
        "number_stories": [1],
        "area": [1000],
        "building_cost": [100000],
        "content_cost": [50000],
        "inventory_cost": [0.0],
        "Longitude": [-157.0],
        "Latitude": [21.0],
    })

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")

    mb = MillimanBuildings(gdf)

    # Assert that the underlying GeoDataFrame has at least one record
    assert len(mb.gdf) >= 1
