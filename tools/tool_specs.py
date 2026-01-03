# OpenAI-style tool schema definitions (JSON-schema-like).
# AI can only call supported operations.

geospatial_tools = [
    {
        "type": "function",
        "function": {
            "name": "show_location",
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
            "name": "buffer_location",
            "description": "Draws a circular buffer around a known location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {
                        "type": "string",
                        "description": "Known place name (e.g., 'utrecht centraal')."
                    },
                    "radius_m": {
                        "type": "number",
                        "description": "Buffer distance in meters."
                    }
                },
                "required": ["place", "radius_m"]
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
            "radius_m": { "type": "number", "description": "Buffer radius in meters", "default": 300 },
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
            "radius_m": {"type": "number", "description": "Radius in meters", "default": 300},
            },
            "required": ["lat", "lon"],
        },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buildings_higher_than_within_buffer",
            "description": "In Utrecht, find buildings within radius of a point that are higher than min_height_m. Returns stats and a GeoJSON URL for rendering.",
            "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "radius_m": {"type": "number", "default": 300},
                "min_height_m": {"type": "number", "default": 30}
            },
            "required": ["lat", "lon"]
            }
        }
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "height_stats_within_buffer",
    #         "description": "Compute min/avg/max building height within radius (meters) of a point (Utrecht only). Height = b3_h_nok - b3_h_maaiveld.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "lat": {"type": "number"},
    #                 "lon": {"type": "number"},
    #                 "radius_m": {"type": "number", "default": 500}
    #             },
    #             "required": ["lat", "lon"]
    #         }
    #     }
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "tallest_building_within_buffer",
    #         "description": "Find the tallest building within radius (meters) of a point (Utrecht only). Returns marker on tallest and optional GeoJSON.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "lat": {"type": "number"},
    #                 "lon": {"type": "number"},
    #                 "radius_m": {"type": "number", "default": 300},
    #                 "export_geojson": {"type": "boolean", "default": True}
    #             },
    #             "required": ["lat", "lon"]
    #         }
    #     }
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "footprint_stats_within_buffer",
    #         "description": "Compute min/avg/max building footprint area (m²) within radius (meters) of a point (Utrecht only). Uses b3_opp_grond if available.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "lat": {"type": "number"},
    #                 "lon": {"type": "number"},
    #                 "radius_m": {"type": "number", "default": 400}
    #             },
    #             "required": ["lat", "lon"]
    #         }
    #     }
    # },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "total_volume_within_buffer",
    #         "description": "Compute total building volume (m³) within radius (meters) of a point (Utrecht only). Prefers b3_volume_lod22/13/12, else footprint*height.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "lat": {"type": "number"},
    #                 "lon": {"type": "number"},
    #                 "radius_m": {"type": "number", "default": 500}
    #             },
    #             "required": ["lat", "lon"]
    #         }
    #     }
    # },


]
