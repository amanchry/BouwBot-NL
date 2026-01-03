from __future__ import annotations
from typing import Dict, Any, Callable


from tools.functions import (
    geocode_location,
    buffer_location,
    buffer_point
)
from tools.buildings_analysis import buildings_within_buffer,buildings_higher_than_within_buffer , height_stats_within_buffer, tallest_building_within_buffer,footprint_stats_within_buffer,total_volume_within_buffer


ToolFn = Callable[..., Dict[str, Any]]

TOOL_REGISTRY: Dict[str, ToolFn] = {
    "geocode_location": geocode_location,
     "buffer_point": buffer_point,
    "buildings_within_buffer": buildings_within_buffer,
    "buildings_higher_than_within_buffer": buildings_higher_than_within_buffer,
    "height_stats_within_buffer": height_stats_within_buffer,
    "tallest_building_within_buffer": tallest_building_within_buffer,
    "footprint_stats_within_buffer": footprint_stats_within_buffer,
    "total_volume_within_buffer": total_volume_within_buffer,

}


def call_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name not in TOOL_REGISTRY:
        return {"ok": False, "message": f"Unknown tool: {tool_name}"}

    fn = TOOL_REGISTRY[tool_name]
    return fn(**args)
