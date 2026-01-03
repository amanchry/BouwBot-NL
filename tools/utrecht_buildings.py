import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import uuid
import json

# -----------------------------
# Configure your dataset path
# -----------------------------
BUILDING_GPKG_PATH = "static/data/utrecht_pand_clip.gpkg"
BUILDING_LAYER_NAME = "pand_utrecht"
UTRECHT_BOUNDARY_PATH = "static/data/utrecht.geojson"

# Utrecht city center (fallback if you need a default)
BUILDING_DEFAULT_CENTER = (52.0907, 5.1214)  # (lat, lon)

MAX_EXPORT_FEATURES = 5000     # hard cap features sent to frontend


OUTPUT_DIR = "output"         
HEIGHT_TOP_COL = "b3_h_nok"
HEIGHT_GROUND_COL = "b3_h_maaiveld"
FOOTPRINT_COL = "b3_opp_grond"      # footprint ground area (m²) if present
VOLUME_COLS = ["b3_volume_lod22", "b3_volume_lod13", "b3_volume_lod12"]  # m³


def _find_height_column(gdf: gpd.GeoDataFrame) -> Optional[str]:
    """
    Best-effort guess of height column name.
    """
    candidates = ["height", "hoogte", "h", "max_height", "building_height", "hoogte_m"]
    cols = {c.lower(): c for c in gdf.columns}
    for key in candidates:
        if key in cols:
            return cols[key]
    return None


@lru_cache(maxsize=1)
def load_buildings() -> Tuple[gpd.GeoDataFrame, Optional[str]]:
    """
    Load buildings once and cache in memory.
    Ensures CRS is EPSG:28992 (RD New) for distance in meters.
    """
    if not os.path.exists(BUILDING_GPKG_PATH):
        raise FileNotFoundError(f"BUILDING_GPKG_PATH not found: {BUILDING_GPKG_PATH}")

    if BUILDING_LAYER_NAME:
        gdf = gpd.read_file(BUILDING_GPKG_PATH, layer=BUILDING_LAYER_NAME)
    else:
        # Auto pick the first layer
        layers = gpd.io.file.fiona.listlayers(BUILDING_GPKG_PATH)
        if not layers:
            raise ValueError("No layers found in GeoPackage.")
        gdf = gpd.read_file(BUILDING_GPKG_PATH, layer=layers[0])

    if gdf.empty:
        raise ValueError("Buildings layer loaded but is empty.")

    if gdf.crs is None:
        raise ValueError("GeoPackage layer has no CRS. Please set it (e.g., EPSG:28992).")

    # Convert to RD New for meter-based buffers
    if str(gdf.crs).lower() not in ["epsg:28992", "28992"]:
        gdf = gdf.to_crs(epsg=28992)

    # Ensure valid geometries
    gdf = gdf[gdf.geometry.notna()].copy()

    height_col = _find_height_column(gdf)

    # Build spatial index implicitly by geopandas when needed (rtree/pygeos)
    return gdf, height_col


def _to_rd_point(lat: float, lon: float) -> Point:
    """
    Convert WGS84 lat/lon to EPSG:28992 point.
    """
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
    x, y = transformer.transform(lon, lat)
    return Point(x, y)


def export_hits_to_geojson_file(hits: gpd.GeoDataFrame, filename_prefix="filtered_buildings") -> str:
    """
    Exports hits to WGS84 GeoJSON and returns filename (not full path).
    """
    # simplify in meters (RD)
    # try:
    #     hits = hits.copy()
    #     hits["geometry"] = hits.geometry.simplify(SIMPLIFY_TOL_M, preserve_topology=True)
    # except Exception:
    #     pass

    # convert to WGS84
    hits = hits.to_crs(epsg=4326)

    # keep only geometry + a couple fields if you want (optional)
    keep_cols = [c for c in hits.columns if c != "geometry"]
    # optionally reduce attributes:
    # keep_cols = [c for c in ["bag_id", "pand_id", "hoogte"] if c in hits.columns]
    hits = hits[keep_cols + ["geometry"]]

    # fname = f"{filename_prefix}_{uuid.uuid4().hex}.geojson"
    fname = f"{filename_prefix}.geojson"
    out_path = os.path.join(OUTPUT_DIR, fname)  # relative to app root

    # write file
    hits.to_file(out_path, driver="GeoJSON")
    return fname


@lru_cache(maxsize=1)
def _load_utrecht_boundary_union():
    """
    Load Utrecht boundary once and cache it.
    Returns a single Shapely geometry (union of all features).
    Ensures CRS is EPSG:4326 for lat/lon checks.
    """
    if not os.path.exists(UTRECHT_BOUNDARY_PATH):
        raise FileNotFoundError(f"Boundary file not found: {UTRECHT_BOUNDARY_PATH}")

    gdf = gpd.read_file(UTRECHT_BOUNDARY_PATH)

    # if gdf.empty:
    #     raise ValueError("Utrecht boundary GeoJSON is empty.")

    # if gdf.crs is None:
    #     # If your GeoJSON has no CRS, assume WGS84 (most GeoJSON is EPSG:4326)
    #     gdf = gdf.set_crs(epsg=4326)

    # if gdf.crs.to_epsg() != 4326:
    #     gdf = gdf.to_crs(epsg=4326)

    # Merge all boundary features into one geometry
    return gdf.geometry.unary_union


def is_point_in_utrecht(lat: float, lon: float) -> bool:
    """
    True if the point is inside Utrecht boundary polygon.
    Uses 'covers' so boundary edge counts as inside.
    """
    boundary = _load_utrecht_boundary_union()
    pt = Point(float(lon), float(lat))  # shapely uses (x,y) = (lon,lat)
    return boundary.covers(pt)



def buildings_within_buffer(
    lat: float,
    lon: float,
    radius_m: float = 300.0,
) -> Dict[str, Any]:
    """

    Inputs:
      lat, lon: WGS84
      radius_m: buffer radius in meters
      limit: cap results so UI stays light

    Returns:
      dict with ok, summary, count, sample, and map instructions.
    """
    if not is_point_in_utrecht(lat, lon):
        return {
            "ok": False,
            "error": "This demo currently supports only Utrecht. Please choose a location within Utrecht.",
        }

    if radius_m <= 0 or radius_m > 15000:
        return {"ok": False, "error": "radius_m must be between 1 and 15000 meters for this demo."}

    gdf, height_col = load_buildings()

    pt_rd = _to_rd_point(lat, lon)
    buf = pt_rd.buffer(radius_m)

    # Fast spatial filter using sindex
    # 1) bbox prefilter
    possible_idx = list(gdf.sindex.intersection(buf.bounds))
    if not possible_idx:
        return {
            "ok": True,
            "count": 0,
            "summary": f"No buildings found within {int(radius_m)}m.",
            "map": {
                "center": [lat, lon],
                "zoom": 14,
                "layers": [
                    {"type": "marker", "lat": lat, "lon": lon, "label": "Query point"},
                    {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
                ],
            },
        }

    candidates = gdf.iloc[possible_idx]
    hits = candidates[candidates.intersects(buf)].copy()

    count = int(len(hits))
    export_hits = hits
    truncated = False
    if count > MAX_EXPORT_FEATURES:
        export_hits = hits.iloc[:MAX_EXPORT_FEATURES].copy()
        truncated = True


    geojson_filename = export_hits_to_geojson_file(export_hits, "filtered_buildings")

    return {
        "ok": True,
        "count": count,
        "summary": (
            f"Found {count} buildings within {int(radius_m)}m."
            + (f" Exported first {MAX_EXPORT_FEATURES} buildings to GeoJSON." if truncated else " Exported results to GeoJSON.")
        ),
        "map": {
            "center": [lat, lon],
            "zoom": 14,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": f"Center ({int(radius_m)}m)"},
                {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
                {"type": "geojson_url", "name": "Filtered buildings", "url": f"/{OUTPUT_DIR}/{geojson_filename}"}
            ],
        },
    }


# -----------------------------
# Height analysis within buffer 
# -----------------------------
def buildings_higher_than_within_buffer(
    lat: float,
    lon: float,
    radius_m: float = 300.0,
    min_height_m: float = 30.0,
) -> dict:
    """
    Height analysis tool:
      - filter buildings in buffer
      - compute height_m = b3_h_nok - b3_h_maaiveld
      - return stats + optionally export GeoJSON for rendering
    """
    if not is_point_in_utrecht(lat, lon):
        return {"ok": False, "error": "Utrecht only."}

    if radius_m <= 0 or radius_m > 15000:
        return {"ok": False, "error": "radius_m must be 1..15000."}

    gdf, _ = load_buildings()  # already in EPSG:28992
    pt_rd = _to_rd_point(lat, lon)
    buf = pt_rd.buffer(radius_m)

    possible_idx = list(gdf.sindex.intersection(buf.bounds))
    if not possible_idx:
        return {
            "ok": True,
            "summary": f"No buildings found within {int(radius_m)}m.",
            "map": {
                "center": [lat, lon],
                "zoom": 14,
                "layers": [
                    {"type": "marker", "lat": lat, "lon": lon, "label": "Query point"},
                    {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
                ],
            },
        }

    candidates = gdf.iloc[possible_idx]
    hits = candidates[candidates.intersects(buf)].copy()
    count = int(len(hits))
    print("total",count)
    if hits.empty:
        return {
            "ok": True,
            "summary": f"No buildings found within {int(radius_m)}m.",
            "map": {
                "center": [lat, lon],
                "zoom": 14,
                "layers": [
                    {"type": "marker", "lat": lat, "lon": lon, "label": "Query point"},
                    {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
                ],
            },
        }
    
    HEIGHT_TOP_COL = "b3_h_nok"
    HEIGHT_GROUND_COL = "b3_h_maaiveld"

    # compute height_m
    if HEIGHT_TOP_COL not in hits.columns:
        return {"ok": False, "error": f"Missing column {HEIGHT_TOP_COL} in dataset."}

    if HEIGHT_GROUND_COL in hits.columns:
        hits["height_m"] = hits[HEIGHT_TOP_COL] - hits[HEIGHT_GROUND_COL]
    else:
        # fallback (absolute height)
        hits["height_m"] = hits[HEIGHT_TOP_COL]

    # drop invalid heights
    hits = hits[hits["height_m"].notna()]
    hits = hits[hits["height_m"] >= 0]

    # filter
    filtered = hits[hits["height_m"] >= float(min_height_m)].copy()
    total_in_buffer = int(len(hits))
    count = int(len(filtered))
    print("filter_count_wiht_height",count)

    # stats
    stats = {}
    if count > 0:
        stats = {
            "min_m": float(filtered["height_m"].min()),
            "max_m": float(filtered["height_m"].max()),
            "avg_m": float(filtered["height_m"].mean()),
        }

    resp = {
        "ok": True,
        "count": count,
        "total_in_buffer": total_in_buffer,
        "min_height_m": float(min_height_m),
        "stats": stats,
        "summary": (
            f"Within {int(radius_m)}m: {count} / {total_in_buffer} buildings are ≥ {min_height_m}m."
            + (f" (min={stats.get('min_m'):.1f}, avg={stats.get('avg_m'):.1f}, max={stats.get('max_m'):.1f})" if stats else "")
        ),
        "map": {
            "center": [lat, lon],
            "zoom": 14,
            "layers": [
                {"type": "marker", "lat": lat, "lon": lon, "label": f"≥{min_height_m}m filter"},
                {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
            ],
        },
    }

    # If nothing to render, return summary only
    if count == 0:
        return resp

    # Too many -> summary only (no heavy export/render)
    if count > MAX_EXPORT_FEATURES:
        resp["summary"] += f" Too many buildings to render (>{MAX_EXPORT_FEATURES}). Showing summary only."
        return resp

    # Export GeoJSON file (cap)
    export_df = filtered
    truncated = False
    if count > MAX_EXPORT_FEATURES:
        export_df = filtered.iloc[:MAX_EXPORT_FEATURES].copy()
        truncated = True

    geojson_filename = export_hits_to_geojson_file(export_df, "filtered_buildings")

    resp["map"]["layers"].append({
        "type": "geojson_url",
        "name": "Height filtered buildings",
        "url": f"/{OUTPUT_DIR}/{geojson_filename}",
    })

    if truncated:
        resp["summary"] += f" Exported first {MAX_EXPORT_FEATURES} buildings."

    return resp




# def _compute_height_m(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
#     """
#     Adds/overwrites height_m column:
#     height_m = b3_h_nok - b3_h_maaiveld (preferred)
#     fallback: height_m = b3_h_nok
#     """
#     out = gdf.copy()

#     if HEIGHT_TOP_COL not in out.columns:
#         raise ValueError(f"Missing required column: {HEIGHT_TOP_COL}")

#     if HEIGHT_GROUND_COL in out.columns:
#         out["height_m"] = out[HEIGHT_TOP_COL] - out[HEIGHT_GROUND_COL]
#     else:
#         out["height_m"] = out[HEIGHT_TOP_COL]

#     out = out[out["height_m"].notna()].copy()
#     out = out[out["height_m"] >= 0].copy()
#     return out


# def _compute_footprint_m2(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
#     """
#     Adds/overwrites footprint_m2 column:
#     - prefer b3_opp_grond if present
#     - else use geometry.area (in EPSG:28992 => m²)
#     """
#     out = gdf.copy()

#     if FOOTPRINT_COL in out.columns:
#         out["footprint_m2"] = out[FOOTPRINT_COL]
#     else:
#         out["footprint_m2"] = out.geometry.area

#     out = out[out["footprint_m2"].notna()].copy()
#     out = out[out["footprint_m2"] >= 0].copy()
#     return out



# def _compute_volume_m3(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
#     """
#     Adds/overwrites volume_m3 column:
#     - prefer b3_volume_lod22, else lod13, else lod12
#     - else fallback to footprint_m2 * height_m
#     """
#     out = gdf.copy()

#     # choose best available volume column
#     vol_col = next((c for c in VOLUME_COLS if c in out.columns), None)

#     if vol_col is not None:
#         out["volume_m3"] = out[vol_col]
#     else:
#         # fallback requires footprint + height
#         out = _compute_height_m(out)
#         out = _compute_footprint_m2(out)
#         out["volume_m3"] = out["footprint_m2"] * out["height_m"]

#     out = out[out["volume_m3"].notna()].copy()
#     out = out[out["volume_m3"] >= 0].copy()
#     return out




# def height_stats_within_buffer(
#     lat: float,
#     lon: float,
#     radius_m: float = 500.0,
# ) -> Dict[str, Any]:
#     """Average/min/max building height within radius_m of (lat, lon)."""
#     if not is_point_in_utrecht(lat, lon):
#         return {"ok": False, "error": "Utrecht only. Please select a point inside Utrecht."}

#     if radius_m <= 0 or radius_m > 15000:
#         return {"ok": False, "error": "radius_m must be between 1 and 15000 meters."}

#     gdf, _ = load_buildings()  # EPSG:28992
#     hits = _get_hits_in_buffer(gdf, lat, lon, radius_m)

#     if hits.empty:
#         return {
#             "ok": True,
#             "count": 0,
#             "stats": {},
#             "summary": f"No buildings found within {int(radius_m)}m.",
#             "map": {
#                 "center": [lat, lon],
#                 "zoom": 14,
#                 "layers": [
#                     {"type": "marker", "lat": lat, "lon": lon, "label": "Query point"},
#                     {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
#                 ],
#             },
#         }

#     hits = _compute_height_m(hits)
#     if hits.empty:
#         return {"ok": True, "count": 0, "stats": {}, "summary": "No valid height values in this area."}

#     stats = {
#         "min_m": float(hits["height_m"].min()),
#         "avg_m": float(hits["height_m"].mean()),
#         "max_m": float(hits["height_m"].max()),
#     }

#     return {
#         "ok": True,
#         "count": int(len(hits)),
#         "stats": stats,
#         "summary": (
#             f"Within {int(radius_m)}m: "
#             f"min={stats['min_m']:.1f}m, avg={stats['avg_m']:.1f}m, max={stats['max_m']:.1f}m "
#             f"(n={len(hits)})."
#         ),
#         "map": {
#             "center": [lat, lon],
#             "zoom": 14,
#             "layers": [
#                 {"type": "marker", "lat": lat, "lon": lon, "label": f"Height stats ({int(radius_m)}m)"},
#                 {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
#             ],
#         },
#     }

# # ============================================================
# # 2) Tallest building within buffer (returns marker on tallest)
# # ============================================================
# def tallest_building_within_buffer(
#     lat: float,
#     lon: float,
#     radius_m: float = 300.0,
#     export_geojson: bool = True,
# ) -> Dict[str, Any]:
#     """Find the tallest building within radius_m; mark it on map; optional GeoJSON export for rendering."""
#     if not is_point_in_utrecht(lat, lon):
#         return {"ok": False, "error": "Utrecht only. Please select a point inside Utrecht."}

#     if radius_m <= 0 or radius_m > 15000:
#         return {"ok": False, "error": "radius_m must be between 1 and 15000 meters."}

#     gdf, _ = load_buildings()
#     hits = _get_hits_in_buffer(gdf, lat, lon, radius_m)

#     if hits.empty:
#         return {"ok": True, "count": 0, "summary": f"No buildings found within {int(radius_m)}m."}

#     hits = _compute_height_m(hits)
#     if hits.empty:
#         return {"ok": True, "count": 0, "summary": "No valid height values in this area."}

#     tallest = hits.loc[hits["height_m"].idxmax()].copy()

#     # centroid in RD, then to lat/lon
#     cent_rd = tallest.geometry.representative_point()
#     t_lat, t_lon = _rd_to_wgs84_point(cent_rd)

#     height_m = float(tallest["height_m"])
#     bid = tallest.get("identificatie", None)

#     resp: Dict[str, Any] = {
#         "ok": True,
#         "count": int(len(hits)),
#         "tallest": {"id": bid, "height_m": height_m},
#         "summary": f"Tallest building within {int(radius_m)}m is {height_m:.1f}m" + (f" (id={bid})." if bid else "."),
#         "map": {
#             "center": [lat, lon],
#             "zoom": 15,
#             "layers": [
#                 {"type": "marker", "lat": lat, "lon": lon, "label": "Query point"},
#                 {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
#                 {"type": "marker", "lat": t_lat, "lon": t_lon, "label": f"Tallest: {height_m:.1f}m"},
#             ],
#         },
#     }

#     # Optionally export just the tallest building geometry for display
#     if export_geojson:
#         gdf_tallest = gpd.GeoDataFrame([tallest], crs=hits.crs)
#         # keep a few useful attributes
#         keep_cols = [c for c in ["identificatie", "height_m", HEIGHT_TOP_COL, HEIGHT_GROUND_COL] if c in gdf_tallest.columns]
#         gdf_tallest = gdf_tallest[keep_cols + ["geometry"]]
#         url = _export_geojson_file(gdf_tallest, prefix="tallest_building")
#         resp["map"]["layers"].append({"type": "geojson_url", "name": "Tallest building", "url": url})

#     return resp

# # ============================================================
# # 3) Footprint area stats (min/avg/max) within buffer
# # ============================================================
# def footprint_stats_within_buffer(
#     lat: float,
#     lon: float,
#     radius_m: float = 400.0,
# ) -> Dict[str, Any]:
#     """Average/min/max building footprint area (m²) within radius_m."""
#     if not is_point_in_utrecht(lat, lon):
#         return {"ok": False, "error": "Utrecht only. Please select a point inside Utrecht."}

#     if radius_m <= 0 or radius_m > 15000:
#         return {"ok": False, "error": "radius_m must be between 1 and 15000 meters."}

#     gdf, _ = load_buildings()
#     hits = _get_hits_in_buffer(gdf, lat, lon, radius_m)

#     if hits.empty:
#         return {"ok": True, "count": 0, "stats": {}, "summary": f"No buildings found within {int(radius_m)}m."}

#     hits = _compute_footprint_m2(hits)
#     if hits.empty:
#         return {"ok": True, "count": 0, "stats": {}, "summary": "No valid footprint areas in this area."}

#     stats = {
#         "min_m2": float(hits["footprint_m2"].min()),
#         "avg_m2": float(hits["footprint_m2"].mean()),
#         "max_m2": float(hits["footprint_m2"].max()),
#     }

#     return {
#         "ok": True,
#         "count": int(len(hits)),
#         "stats": stats,
#         "summary": (
#             f"Within {int(radius_m)}m: "
#             f"footprint min={stats['min_m2']:.1f} m², avg={stats['avg_m2']:.1f} m², max={stats['max_m2']:.1f} m² "
#             f"(n={len(hits)})."
#         ),
#         "map": {
#             "center": [lat, lon],
#             "zoom": 14,
#             "layers": [
#                 {"type": "marker", "lat": lat, "lon": lon, "label": f"Footprint stats ({int(radius_m)}m)"},
#                 {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
#             ],
#         },
#     }

# # ============================================================
# # 4) Total building volume within buffer
# # ============================================================
# def total_volume_within_buffer(
#     lat: float,
#     lon: float,
#     radius_m: float = 500.0,
# ) -> Dict[str, Any]:
#     """Total building volume (m³) within radius_m. Uses LOD volume columns if present, else area*height."""
#     if not is_point_in_utrecht(lat, lon):
#         return {"ok": False, "error": "Utrecht only. Please select a point inside Utrecht."}

#     if radius_m <= 0 or radius_m > 15000:
#         return {"ok": False, "error": "radius_m must be between 1 and 15000 meters."}

#     gdf, _ = load_buildings()
#     hits = _get_hits_in_buffer(gdf, lat, lon, radius_m)

#     if hits.empty:
#         return {"ok": True, "count": 0, "stats": {}, "summary": f"No buildings found within {int(radius_m)}m."}

#     hits = _compute_volume_m3(hits)
#     if hits.empty:
#         return {"ok": True, "count": 0, "summary": "No valid volume values in this area."}

#     total_m3 = float(hits["volume_m3"].sum())
#     avg_m3 = float(hits["volume_m3"].mean())
#     max_m3 = float(hits["volume_m3"].max())

#     return {
#         "ok": True,
#         "count": int(len(hits)),
#         "stats": {
#             "total_m3": total_m3,
#             "avg_m3": avg_m3,
#             "max_m3": max_m3,
#         },
#         "summary": (
#             f"Within {int(radius_m)}m: total volume ≈ {total_m3:,.0f} m³ "
#             f"(avg={avg_m3:,.0f} m³, max={max_m3:,.0f} m³, n={len(hits)})."
#         ),
#         "map": {
#             "center": [lat, lon],
#             "zoom": 14,
#             "layers": [
#                 {"type": "marker", "lat": lat, "lon": lon, "label": f"Total volume ({int(radius_m)}m)"},
#                 {"type": "circle", "lat": lat, "lon": lon, "radius_m": radius_m},
#             ],
#         },
#     }

