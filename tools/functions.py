from __future__ import annotations

from typing import Dict, Any, Tuple, Optional
import re
import os
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from shapely.geometry import Point
import geopandas as gpd


# ==================================================
# Geocoding (Nominatim)
# ==================================================

GEOCODER = Nominatim(user_agent="bouwbot-nl (contact: chaudharymac2604@gmail.com)")

geocode = RateLimiter(
    GEOCODER.geocode,
    min_delay_seconds=1.1,   # ~1 req/sec
    swallow_exceptions=True
)

_GEOCODE_CACHE: Dict[str, Tuple[float, float]] = {}

_WGS84_TO_RD = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
_RD_TO_WGS84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
OUTPUT_DIR = "output"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def geocode_place(place: str, country_codes: str = "nl") -> Optional[Tuple[float, float]]:
    """
    Convert a place string to (lat, lon) using Nominatim.
    Default constrained to Netherlands (nl).
    """
    key = _normalize(place)
    if key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[key]

    loc = geocode(place, country_codes=country_codes)
    if not loc:
        return None

    lat, lon = float(loc.latitude), float(loc.longitude)
    _GEOCODE_CACHE[key] = (lat, lon)
    return lat, lon






def geocode_location(*, place: str) -> Dict[str, Any]:
    coords = geocode_place(place)
    if not coords:
        return {"ok": False, "tool": "show_location", "message": f"Could not geocode: {place}"}

    lat, lon = coords
    return {
        "ok": True,
        "tool": "show_location",
        "place": place,
        "lat": lat,
        "lon": lon,
        "map": {
            "center": [lat, lon],
            "zoom": 13,
            "layers": [{"type": "marker", "lat": lat, "lon": lon, "label": place}],
        },
        "message": f"Showing **{place}** on the map."
    }


def export_gpd_to_geojson_file(gpd: gpd.GeoDataFrame, filename_prefix) -> str:
    """
    Exports gpd to WGS84 GeoJSON and returns filename (not full path).
    """
    # simplify in meters (RD)
    # try:
    #     gpd = gpd.copy()
    #     gpd["geometry"] = gpd.geometry.simplify(SIMPLIFY_TOL_M, preserve_topology=True)
    # except Exception:
    #     pass

    # convert to WGS84
    gpd = gpd.to_crs(epsg=4326)

    # keep only geometry + a couple fields if you want (optional)
    keep_cols = [c for c in gpd.columns if c != "geometry"]
    # optionally reduce attributes:
    # keep_cols = [c for c in ["bag_id", "pand_id", "hoogte"] if c in gpd.columns]
    gpd = gpd[keep_cols + ["geometry"]]

    # fname = f"{filename_prefix}_{uuid.uuid4().hex}.geojson"
    fname = f"{filename_prefix}.geojson"
    out_path = os.path.join(OUTPUT_DIR, fname)  # relative to app root

    # write file
    gpd.to_file(out_path, driver="GeoJSON")
    return fname



def buffer_location(*, place: str, radius_m: int) -> Dict[str, Any]:
    coords = geocode_place(place)
    if not coords:
        return {"ok": False, "tool": "buffer_location", "message": f"Could not geocode: {place}"}

    lat, lon = coords

    x, y = _WGS84_TO_RD.transform(float(lon), float(lat))
    geom_rd = Point(x, y).buffer(float(radius_m), resolution=64)

    # 2) GeoDataFrame in RD
    gdf = gpd.GeoDataFrame(
        [{"name": place, "radius_m": float(radius_m)}],
        geometry=[geom_rd],
        crs="EPSG:28992",
    )

    fname = export_gpd_to_geojson_file(gdf, f"buffer_geom")

    return {
        "ok": True,
        "tool": "buffer_location",
        "place": place,
        "radius_m": int(radius_m),
        "map": {
            "center": [lat, lon],
            "zoom": 14,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": place},
                { "type": "geojson_url", "name": 'selected location', "url": f"/{OUTPUT_DIR}/{fname}", }
            ],
        },
        "message": f"Drew a **{radius_m} m** buffer"
    }


def buffer_point(lat: float, lon: float, radius_m: float = 300) -> Dict[str, Any]:
    """
    Creates a buffer visualization around a point.
    lat/lon are WGS84. radius_m is meters.
    """
    try:
        lat = float(lat)
        lon = float(lon)
        radius_m = float(radius_m)
    except Exception:
        return {"ok": False, "error": "Invalid lat/lon/radius_m."}

    if radius_m <= 0 or radius_m > 15000:
        return {"ok": False, "error": "radius_m must be between 1 and 15000 meters."}
    
    x, y = _WGS84_TO_RD.transform(float(lon), float(lat))
    geom_rd = Point(x, y).buffer(float(radius_m), resolution=64)

    # 2) GeoDataFrame in RD
    gdf = gpd.GeoDataFrame(
        [{"name": 'Selected point', "radius_m": float(radius_m)}],
        geometry=[geom_rd],
        crs="EPSG:28992",
    )

    fname = export_gpd_to_geojson_file(gdf, f"buffer_geom")

    return {
        "ok": True,
        "summary": f"Drew a {int(radius_m)}m buffer around the selected point.",
        "map": {
            "center": [lat, lon],
            "zoom": 15,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": "Selected point"},
                { "type": "geojson_url", "name": 'Selected point', "url": f"/{OUTPUT_DIR}/{fname}", }
            ],
        },
    }


