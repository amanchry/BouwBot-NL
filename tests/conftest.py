# tests/conftest.py
# Shared pytest fixtures (small synthetic datasets)

import pytest
import geopandas as gpd
from shapely.geometry import Polygon, Point
from unittest.mock import Mock, MagicMock

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


@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client for testing.
    """
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    
    mock_message.content = "Test response"
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_geocode_response():
    """
    Mock geocoding response from Nominatim.
    """
    mock_location = Mock()
    mock_location.latitude = 52.0907
    mock_location.longitude = 5.1214
    return mock_location


@pytest.fixture
def sample_map_state():
    """
    Sample map state for testing.
    """
    return {
        "center": [52.0907, 5.1214],
        "zoom": 13,
        "layers": [
            {"type": "marker", "lat": 52.0907, "lon": 5.1214, "label": "Utrecht"}
        ]
    }


@pytest.fixture
def utrecht_boundary_geometry():
    """
    Mock Utrecht boundary as a simple polygon for testing.
    """
    return Polygon([
        (5.0, 52.0),   # SW
        (5.2, 52.0),   # SE
        (5.2, 52.2),  # NE
        (5.0, 52.2),  # NW
        (5.0, 52.0)
    ])


@pytest.fixture
def sample_tool_result():
    """
    Sample tool result for testing.
    """
    return {
        "ok": True,
        "summary": "Test operation completed",
        "map": {
            "center": [52.0907, 5.1214],
            "zoom": 14,
            "layers": [
                {"type": "marker", "lat": 52.0907, "lon": 5.1214}
            ]
        }
    }


@pytest.fixture
def sample_geodataframe_wgs84():
    """
    Sample GeoDataFrame in WGS84 for testing.
    """
    return gpd.GeoDataFrame(
        [{"id": 1, "name": "test"}],
        geometry=[Point(5.1214, 52.0907)],
        crs="EPSG:4326"
    )


@pytest.fixture
def sample_geodataframe_rd():
    """
    Sample GeoDataFrame in RD New for testing.
    """
    return gpd.GeoDataFrame(
        [{"id": 1, "name": "test"}],
        geometry=[Point(130000, 455000)],
        crs="EPSG:28992"
    )
