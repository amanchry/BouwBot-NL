# tests/test_utrecht_buildings.py
# Unit tests for Utrecht building analysis tools

from shapely.geometry import Point
from pyproj import Transformer
import tools.buildings_analysis as tb


def rd_to_wgs84(x, y):
    """
    Convert RD New (EPSG:28992) to WGS84 (lat, lon).
    """
    transformer = Transformer.from_crs(
        "EPSG:28992", "EPSG:4326", always_xy=True
    )
    lon, lat = transformer.transform(x, y)
    return lat, lon


def test_buildings_within_buffer(monkeypatch, sample_buildings_gdf_28992, rd_point_near_A):
    """
    Buildings within 250m buffer around A → includes A & B, excludes C.
    """

    # Always allow Utrecht boundary
    monkeypatch.setattr(tb, "is_point_in_utrecht", lambda lat, lon: True)

    # Use synthetic buildings instead of real dataset
    monkeypatch.setattr(tb, "load_buildings", lambda: (sample_buildings_gdf_28992, "b3_h_nok"))

    # Force RD conversion to known point
    x, y = rd_point_near_A
    monkeypatch.setattr(tb, "_to_rd_point", lambda lat, lon: Point(x, y))

    lat, lon = rd_to_wgs84(x, y)

    result = tb.buildings_within_buffer(
        lat=lat,
        lon=lon,
        radius_m=250,
        limit=10
    )

    assert result["ok"] is True
    assert result["count"] == 2
    assert "map" in result
    assert any(layer["type"] == "circle" for layer in result["map"]["layers"])


def test_height_filter(monkeypatch, sample_buildings_gdf_28992, rd_point_near_A):
    """
    Height = b3_h_nok - b3_h_maaiveld.
    Only building B (60m) should remain when min_height=50.
    """

    monkeypatch.setattr(tb, "is_point_in_utrecht", lambda lat, lon: True)
    monkeypatch.setattr(tb, "load_buildings", lambda: (sample_buildings_gdf_28992, None))

    x, y = rd_point_near_A
    monkeypatch.setattr(tb, "_to_rd_point", lambda lat, lon: Point(x, y))

    # Prevent file export during tests
    if hasattr(tb, "_export_geojson"):
        monkeypatch.setattr(tb, "_export_geojson", lambda gdf, prefix="x": "dummy.geojson")

    lat, lon = rd_to_wgs84(x, y)

    result = tb.buildings_higher_than_within_buffer(
        lat=lat,
        lon=lon,
        radius_m=250,
        min_height_m=50
    )

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["stats"]["max_m"] >= 50
