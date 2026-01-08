"""
Unit Tests for BouwBot NL Flask Application

Test Suite:
1. test_ensure_state - Session initialization
2. test_apply_map_from_tool_result - Map update logic  
3. test_call_tool - Tool dispatch system
4. test_api_chat_endpoint_empty_message - Error handling
5. test_api_reset_endpoint - Session reset
6. test_buffer_point_validation - Input validation

Usage:
    pytest test_app.py -v
"""

import pytest
import json
import os
import shutil
from unittest.mock import patch, MagicMock
from flask import session

# Import the Flask app and functions to test
import sys
# Add parent directory to path so we can import app and tools
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from app import (
    app, 
    ensure_state, 
    apply_map_from_tool_result,
    DEFAULT_MAP_CENTER,
    DEFAULT_MAP_ZOOM
)
from tools.tool_registry import call_tool
from tools.functions import buffer_point


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def clean_output_dir():
    """Ensure output directory exists and clean it after tests."""
    # Get path relative to project root (parent of tests dir)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(project_root, "output")
    
    # Create the directory
    os.makedirs(output_dir, exist_ok=True)
    
    # IMPORTANT: Change to project root so relative "output" path works
    original_cwd = os.getcwd()
    os.chdir(project_root)
    
    yield output_dir
    
    # Restore original working directory
    os.chdir(original_cwd)
    
    # Cleanup after test
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")


# ============================================================
# TEST 1: test_ensure_state
# ============================================================

def test_ensure_state(client):
    """
    Test that ensure_state() initializes session with correct defaults
    and doesn't overwrite existing data.
    """
    # Test 1: Initial state should be empty
    with client.session_transaction() as sess:
        # Session should be empty initially
        assert 'messages' not in sess
        assert 'map_center' not in sess
    
    # Call ensure_state by making a request
    client.get('/')  # This triggers ensure_state()
    
    # Verify defaults are set
    with client.session_transaction() as sess:
        assert 'messages' in sess
        assert 'map_center' in sess
        assert 'map_zoom' in sess
        assert 'map_layers' in sess
        
        assert sess['messages'] == []
        assert sess['map_center'] == DEFAULT_MAP_CENTER
        assert sess['map_zoom'] == DEFAULT_MAP_ZOOM
        assert sess['map_layers'] == []
    
    # Test 2: Verify it doesn't overwrite existing data
    with client.session_transaction() as sess:
        sess['messages'] = [{"role": "user", "content": "test"}]
        sess['map_center'] = [50.0, 6.0]
    
    client.get('/')  # Triggers ensure_state again
    
    # Original data should be preserved
    with client.session_transaction() as sess:
        assert sess['messages'] == [{"role": "user", "content": "test"}]
        assert sess['map_center'] == [50.0, 6.0]


# ============================================================
# TEST 2: test_apply_map_from_tool_result
# ============================================================

def test_apply_map_from_tool_result(client):
    """
    Test that apply_map_from_tool_result correctly updates session
    based on tool result structure.
    """
    # Initialize session
    client.get('/')
    
    # Test 1: Valid map data with all fields
    tool_result = {
        "ok": True,
        "map": {
            "center": [52.09, 5.12],
            "zoom": 15,
            "layers": [{"type": "marker", "lat": 52.09, "lon": 5.12}]
        }
    }
    
    # Need to call the function within a request context
    with client.application.test_request_context():
        with client.session_transaction() as sess:
            # Manually set session to mimic active request
            from flask import session as flask_session
            flask_session.update(sess)
            
            result = apply_map_from_tool_result(tool_result)
            assert result is True
            
            # Check the updated session
            assert flask_session['map_center'] == [52.09, 5.12]
            assert flask_session['map_zoom'] == 15
            assert len(flask_session['map_layers']) == 1
    
    # Test 2: Partial map data (only center)
    tool_result = {
        "ok": True,
        "map": {
            "center": [53.0, 6.0]
        }
    }
    
    with client.application.test_request_context():
        with client.session_transaction() as sess:
            from flask import session as flask_session
            flask_session.update(sess)
            
            result = apply_map_from_tool_result(tool_result)
            assert result is True
            assert flask_session['map_center'] == [53.0, 6.0]
    
    # Test 3: No map data (ok=False)
    tool_result = {
        "ok": False,
        "error": "Some error"
    }
    
    with client.application.test_request_context():
        with client.session_transaction() as sess:
            from flask import session as flask_session
            flask_session.update(sess)
            old_center = flask_session['map_center']
            
            result = apply_map_from_tool_result(tool_result)
            assert result is False
            assert flask_session['map_center'] == old_center  # No change
    
    # Test 4: ok=True but no map field
    tool_result = {
        "ok": True,
        "count": 5
    }
    
    with client.application.test_request_context():
        with client.session_transaction() as sess:
            from flask import session as flask_session
            flask_session.update(sess)
            old_center = flask_session['map_center']
            
            result = apply_map_from_tool_result(tool_result)
            assert result is False
            assert flask_session['map_center'] == old_center  # No change


# ============================================================
# TEST 3: test_call_tool
# ============================================================

def test_call_tool():
    """
    Test that call_tool correctly dispatches to registered tools
    and handles unknown tools.
    """
    # Test 1: Unknown tool name
    result = call_tool("nonexistent_tool", {})
    assert result['ok'] is False
    assert 'Unknown tool' in result['message']
    assert 'nonexistent_tool' in result['message']
    
    # Test 2: Valid tool with mocked implementation
    with patch('tools.functions.geocode_place') as mock_geocode:
        mock_geocode.return_value = (52.3676, 4.9041)  # Amsterdam coordinates
        
        result = call_tool("geocode_location", {"place": "amsterdam"})
        
        assert result['ok'] is True
        assert 'lat' in result
        assert 'lon' in result
        assert result['place'] == 'amsterdam'
        mock_geocode.assert_called_once_with("amsterdam")


# ============================================================
# TEST 4: test_api_chat_endpoint_empty_message
# ============================================================

def test_api_chat_endpoint_empty_message(client):
    """
    Test that /api/chat endpoint returns 400 error for empty messages.
    """
    # Test with empty string
    response = client.post(
        '/api/chat',
        data=json.dumps({"message": ""}),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['ok'] is False
    assert 'error' in data
    assert 'Empty message' in data['error']
    
    # Test with whitespace only
    response = client.post(
        '/api/chat',
        data=json.dumps({"message": "   "}),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['ok'] is False
    
    # Test with no message field
    response = client.post(
        '/api/chat',
        data=json.dumps({}),
        content_type='application/json'
    )
    
    assert response.status_code == 400


# ============================================================
# TEST 6: test_api_reset_endpoint
# ============================================================

def test_api_reset_endpoint(client):
    """
    Test that /api/reset endpoint clears session and reinitializes state.
    """
    # First, set up some session data
    with client.session_transaction() as sess:
        sess['messages'] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        sess['map_center'] = [52.09, 5.12]
        sess['map_zoom'] = 16
        sess['map_layers'] = [{"type": "marker"}]
    
    # Call reset endpoint
    response = client.post('/api/reset')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['ok'] is True
    
    # Verify session was cleared and reinitialized
    with client.session_transaction() as sess:
        assert sess['messages'] == []
        assert sess['map_center'] == DEFAULT_MAP_CENTER
        assert sess['map_zoom'] == DEFAULT_MAP_ZOOM
        assert sess['map_layers'] == []


# ============================================================
# TEST 7: test_buffer_point_validation
# ============================================================

def test_buffer_point_validation(clean_output_dir):
    """
    Test that buffer_point validates inputs correctly and returns
    proper error messages for invalid inputs.
    """
    # Test 1: Invalid radius - zero
    result = buffer_point(lat=52.09, lon=5.12, radius_m=0)
    assert result['ok'] is False
    assert 'error' in result
    assert 'radius_m must be between 1 and 15000' in result['error']
    
    # Test 2: Invalid radius - negative
    result = buffer_point(lat=52.09, lon=5.12, radius_m=-100)
    assert result['ok'] is False
    assert 'error' in result
    assert 'radius_m must be between 1 and 15000' in result['error']
    
    # Test 3: Invalid radius - too large
    result = buffer_point(lat=52.09, lon=5.12, radius_m=20000)
    assert result['ok'] is False
    assert 'error' in result
    assert 'radius_m must be between 1 and 15000' in result['error']
    
    # Test 4: Valid inputs - should succeed and create GeoJSON file
    result = buffer_point(lat=52.09, lon=5.12, radius_m=500)
    
    assert result['ok'] is True
    assert 'summary' in result
    assert '500m buffer' in result['summary']
    assert 'map' in result
    assert result['map']['center'] == [52.09, 5.12]
    assert result['map']['zoom'] == 15
    assert len(result['map']['layers']) == 2  # marker + geojson
    
    # Verify GeoJSON file was created
    geojson_layer = [l for l in result['map']['layers'] if l['type'] == 'geojson_url'][0]
    geojson_url = geojson_layer['url']
    geojson_filename = geojson_url.split('/')[-1]
    geojson_path = os.path.join(clean_output_dir, geojson_filename)
    
    assert os.path.exists(geojson_path), f"GeoJSON file not created at {geojson_path}"
    
    # Verify it's valid JSON
    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)
        assert 'type' in geojson_data
        assert geojson_data['type'] == 'FeatureCollection'
        assert 'features' in geojson_data
    
    # Test 5: Invalid lat/lon types
    result = buffer_point(lat="invalid", lon=5.12, radius_m=500)
    assert result['ok'] is False
    assert 'error' in result


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
