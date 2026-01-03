# OpenAI-style tool schema definitions (JSON-schema-like).
# AI can only call supported operations.

geospatial_tools = [
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": "Centers the map on a known location and adds a marker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {
                        "type": "string",
                        "description": "Known place name (e.g., 'amsterdam', 'amsterdam centraal')."
                    }
                },
                "required": ["place"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "buffer_point",
        "description": "Draw a circular buffer (meters) around a clicked point (lat/lon)",
        "parameters": {
        "type": "object",
        "properties": {
            "lat": { "type": "number", "description": "Latitude (WGS84)" },
            "lon": { "type": "number", "description": "Longitude (WGS84)" },
            "radius_m": { "type": "number", "description": "Buffer radius in meters", "default": 400 },
        },
        "required": ["lat", "lon"]
        }
        }
    },
    
    {
        "type": "function",
        "function": {
        "name": "buildings_within_buffer",
        "description": "Find buildings within a radius (meters) of a point.",
        "parameters": {
            "type": "object",
            "properties": {
            "lat": {"type": "number", "description": "Latitude (WGS84)"},
            "lon": {"type": "number", "description": "Longitude (WGS84)"},
            "radius_m": {"type": "number", "description": "Radius in meters", "default": 400},
            },
            "required": ["lat", "lon"],
        },
        },
    },
    {
        "type": "function",
        "function": {
        "name": "buildings_higher_than_within_buffer",
        "description": "Find buildings within radius of a point that are higher than min_height_m. Returns stats and a GeoJSON URL for rendering.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "radius_m": {"type": "number", "default": 400},
                "min_height_m": {"type": "number", "default": 30}
            },
        "required": ["lat", "lon"]
        }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "height_stats_within_buffer",
            "description": "Compute min/avg/max building height within radius (meters) of a point. Returns stats and a GeoJSON URL for rendering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "radius_m": {"type": "number", "default": 400}
                },
                "required": ["lat", "lon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tallest_building_within_buffer",
            "description": "Find the tallest building within radius (meters) of a point.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "radius_m": {"type": "number", "default": 400}
                },
                "required": ["lat", "lon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "footprint_stats_within_buffer",
            "description": "Compute min/avg/max building footprint area (m²) within radius (meters) of a point. Returns stats and a GeoJSON URL for rendering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "radius_m": {"type": "number", "default": 400}
                },
                "required": ["lat", "lon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "total_volume_within_buffer",
            "description": "Compute total building volume (m³) within radius (meters) of a point.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "radius_m": {"type": "number", "default": 400}
                },
                "required": ["lat", "lon"]
            }
        }
    },


]
