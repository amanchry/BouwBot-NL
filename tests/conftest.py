# tests/conftest.py
# Shared pytest fixtures (small synthetic datasets)

import pytest
import geopandas as gpd
from shapely.geometry import Polygon

@pytest.fixture
def sample_buildings_gdf_28992():
    """
    Tiny synthetic building dataset in EPSG:28992 (meters).
    Used instead of the real 500MB dataset.
    """

    def square(x, y, size=20):
        return Polygon([
            (x, y),
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
            (x, y),
        ])

    geometries = [
        square(130000, 455000),   # Building A
        square(130200, 455000),   # Building B
        square(131000, 456000),   # Building C (far away)
    ]

    data = {
        "identificatie": ["A", "B", "C"],
        "b3_h_nok": [40.0, 80.0, 25.0],
        "b3_h_maaiveld": [10.0, 20.0, 5.0],
        "geometry": geometries,
    }

    gdf = gpd.GeoDataFrame(data, geometry="geometry", crs="EPSG:28992")
    return gdf


@pytest.fixture
def rd_point_near_A():
    """
    RD New coordinate close to building A.
    """
    return (130010, 455010)
