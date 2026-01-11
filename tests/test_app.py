"""
Unit Tests for BouwBot NL Application

Run:
    pytest -v
"""

import os
import sys
import json
import pytest
from unittest.mock import patch

# Add project root to import path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app import app, DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM, apply_map_from_tool_result
from flask import session as flask_session

from tools.tool_registry import call_tool
from tools.functions import buffer_point  ,geocode_location
from tools.buildings_analysis import buildings_within_buffer



DATASET_PATH = os.path.join(PROJECT_ROOT, "static", "data", "utrecht_pand_clip.gpkg")




# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as c:
        yield c


@pytest.fixture
def clean_output_dir():
    """Ensure output dir exists + clean it after the test."""
    output_dir = os.path.join(PROJECT_ROOT, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Ensure relative "output" writes end up in the project output/
    old_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)

    yield output_dir

    os.chdir(old_cwd)
    for fn in os.listdir(output_dir):
        fp = os.path.join(output_dir, fn)
        if os.path.isfile(fp):
            try:
                os.unlink(fp)
            except Exception:
                pass


# ============================================================
# 1) Session initialization via homepage
# ============================================================
def test_session_initialized_on_homepage(client):
    res = client.get("/")
    assert res.status_code == 200

    with client.session_transaction() as sess:
        assert "messages" in sess
        assert "map_center" in sess
        assert "map_zoom" in sess
        assert "map_layers" in sess

        assert sess["messages"] == []
        assert sess["map_center"] == DEFAULT_MAP_CENTER
        assert sess["map_zoom"] == DEFAULT_MAP_ZOOM
        assert sess["map_layers"] == []


# ============================================================
# 2) apply_map_from_tool_result updates session properly
# ============================================================
def test_apply_map_from_tool_result_updates_session():
    tool_result = {
        "ok": True,
        "map": {
            "center": [52.09, 5.12],
            "zoom": 15,
            "layers": [{"type": "marker", "lat": 52.09, "lon": 5.12}],
        },
    }

    with app.test_request_context("/"):
        # initialize defaults in session
        flask_session["map_center"] = DEFAULT_MAP_CENTER
        flask_session["map_zoom"] = DEFAULT_MAP_ZOOM
        flask_session["map_layers"] = []

        changed = apply_map_from_tool_result(tool_result)
        assert changed is True
        assert flask_session["map_center"] == [52.09, 5.12]
        assert flask_session["map_zoom"] == 15
        assert len(flask_session["map_layers"]) == 1


# ============================================================
# 3) call_tool handles unknown tool gracefully
# ============================================================
def test_call_tool_unknown_tool():
    result = call_tool("nonexistent_tool", {})
    assert result["ok"] is False
    assert "Unknown tool" in result.get("message", "")


# ============================================================
# 4) call_tool geocode tool works (mock geocoding)
# ============================================================
def test_call_tool_geocode_mocked():
    with patch("tools.functions.geocode_place") as mock_geocode:
        mock_geocode.return_value = (52.3676, 4.9041)

        result = call_tool("geocode_location", {"place": "amsterdam"})
        assert result["ok"] is True
        assert "lat" in result and "lon" in result



# ============================================================
# 5) /api/chat rejects empty messages
# ============================================================
def test_api_chat_empty_message(client):
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code == 400
    data = res.get_json()
    assert data["ok"] is False
    assert "Empty message" in data["error"]


# ============================================================
# 6) /api/reset clears session
# ============================================================
def test_api_reset_clears_session(client):
    # Put data into session
    with client.session_transaction() as sess:
        sess["messages"] = [{"role": "user", "content": "hi"}]
        sess["map_center"] = [1, 2]
        sess["map_zoom"] = 99
        sess["map_layers"] = [{"type": "marker"}]

    res = client.post("/api/reset")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True

    with client.session_transaction() as sess:
        assert sess["messages"] == []
        assert sess["map_center"] == DEFAULT_MAP_CENTER
        assert sess["map_zoom"] == DEFAULT_MAP_ZOOM
        assert sess["map_layers"] == []


# ============================================================
# 7) buffer_point validation + output (accept circle OR geojson_url)
# ============================================================
def test_buffer_point_validation_and_output(clean_output_dir):
    # invalid radius
    r = buffer_point(lat=52.09, lon=5.12, radius_m=0)
    assert r["ok"] is False

    # valid
    r = buffer_point(lat=52.09, lon=5.12, radius_m=500)
    assert r["ok"] is True
    assert "map" in r
    assert r["map"]["center"] == [52.09, 5.12]

    layers = r["map"].get("layers", [])
    assert isinstance(layers, list) and len(layers) >= 1

    # Accept either:
    # - geojson_url buffer file
    # - circle layer (legacy frontend circle)
    has_geojson_url = any(l.get("type") == "geojson_url" for l in layers)
    has_circle = any(l.get("type") == "circle" for l in layers)

    assert has_geojson_url or has_circle


# ============================================================
# 8) Tests on Building data
# ============================================================

@pytest.mark.skipif(
    not os.path.exists(DATASET_PATH),
    reason="Building dataset not found: static/data/utrecht_pand_clip.gpkg",
)

def test_buildings_within_buffer_data(clean_output_dir):
    # Utrecht center (should be inside boundary)
    lat, lon = 52.0907, 5.1214

    result = buildings_within_buffer(lat=lat, lon=lon, radius_m=150)

    assert result["ok"] is True
    assert "count" in result
    assert "map" in result
    assert "layers" in result["map"]

    # Should include geojson outputs (buffer + buildings) in your current design
    gj_layers = [l for l in result["map"]["layers"] if l.get("type") == "geojson_url"]
    assert len(gj_layers) >= 1

    # Verify exported files exist
    for layer in gj_layers:
        url = layer["url"]  # e.g. /output/buffer_geom.geojson
        filename = url.split("/")[-1]
        path = os.path.join(clean_output_dir, filename)
        assert os.path.exists(path), f"Expected GeoJSON file missing: {path}"


@pytest.mark.skipif(
    not os.path.exists(DATASET_PATH),
    reason="Building dataset not found: static/data/utrecht_pand_clip.gpkg",
)
def test_buildings_higher_than_within_buffer_data(clean_output_dir):
    from tools.buildings_analysis import buildings_higher_than_within_buffer

    lat, lon = 52.0907, 5.1214  # Utrecht center
    result = buildings_higher_than_within_buffer(lat=lat, lon=lon, radius_m=200, min_height_m=5)

    assert result["ok"] is True
    assert "count" in result
    assert "total_in_buffer" in result
    assert result["count"] <= result["total_in_buffer"]

    # If buildings exist, check stats consistency
    if result["count"] > 0:
        stats = result.get("stats", {})
        assert "min_m" in stats and "avg_m" in stats and "max_m" in stats
        assert stats["min_m"] <= stats["avg_m"] <= stats["max_m"]

    # should include at least buffer geojson layer
    layers = result["map"]["layers"]
    assert any(l.get("type") == "geojson_url" for l in layers)


@pytest.mark.skipif(
    not os.path.exists(DATASET_PATH),
    reason="Building dataset not found: static/data/utrecht_pand_clip.gpkg",
)
def test_height_stats_within_buffer_data(clean_output_dir):
    from tools.buildings_analysis import height_stats_within_buffer

    lat, lon = 52.0907, 5.1214
    result = height_stats_within_buffer(lat=lat, lon=lon, radius_m=200)

    assert result["ok"] is True
    assert "stats" in result

    stats = result["stats"]
    if stats:  # some tools return {} if empty
        assert all(k in stats for k in ["min_m", "avg_m", "max_m"])
        assert isinstance(stats["min_m"], (int, float))
        assert isinstance(stats["avg_m"], (int, float))
        assert isinstance(stats["max_m"], (int, float))
        assert stats["min_m"] <= stats["avg_m"] <= stats["max_m"]


@pytest.mark.skipif(
    not os.path.exists(DATASET_PATH),
    reason="Building dataset not found: static/data/utrecht_pand_clip.gpkg",
)
def test_tallest_building_within_buffer_data(clean_output_dir):
    from tools.buildings_analysis import tallest_building_within_buffer

    lat, lon = 52.0907, 5.1214
    result = tallest_building_within_buffer(lat=lat, lon=lon, radius_m=200)

    assert result["ok"] is True
    assert "tallest" in result or "summary" in result

    # If tool returns a structured object, validate it
    if "tallest" in result and result["tallest"]:
        t = result["tallest"]
        assert "height_m" in t
        assert isinstance(t["height_m"], (int, float))
        assert t["height_m"] >= 0