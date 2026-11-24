from __future__ import annotations

from typing import Any

from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success

from pointcloud_terrain import search_candidates


@skill_entry
def main(
    south: float,
    west: float,
    north: float,
    east: float,
    endpoint: str = "https://tnmaccess.nationalmap.gov/api/v1/products",
    **_: Any,
) -> dict:
    """List bounded USGS 3DEP lidar point cloud tile candidates for a bbox."""
    try:
        result = search_candidates(south, west, north, east, endpoint)
        return skill_success(
            "USGS 3DEP point cloud candidates listed",
            bbox=result["bbox"],
            candidate_count=result["count"],
            candidates=result["candidates"],
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to list USGS 3DEP point cloud candidates")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
