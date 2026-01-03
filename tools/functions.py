from __future__ import annotations

from typing import Dict, Any, Tuple, Optional
import re

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


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


def show_location(*, place: str) -> Dict[str, Any]:
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


def buffer_location(*, place: str, distance_m: int) -> Dict[str, Any]:
    coords = geocode_place(place)
    if not coords:
        return {"ok": False, "tool": "buffer_location", "message": f"Could not geocode: {place}"}

    lat, lon = coords
    return {
        "ok": True,
        "tool": "buffer_location",
        "place": place,
        "distance_m": int(distance_m),
        "map": {
            "center": [lat, lon],
            "zoom": 14,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": place},
                {"type": "circle", "lat": lat, "lon": lon, "radius_m": int(distance_m)},
            ],
        },
        "message": f"Drew a **{distance_m} m** buffer around **{place}**."
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

    return {
        "ok": True,
        "summary": f"Drew a {int(radius_m)}m buffer around the selected point.",
        "map": {
            "center": [lat, lon],
            "zoom": 15,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": "Selected point"},
                {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
            ],
        },
    }


