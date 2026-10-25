from __future__ import annotations

import os
import urllib.parse
from typing import Any

from dcc_mcp_core.asset_import import AssetAttribution, AssetDescriptor, AssetFileVariant
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success

from _tnm import (
    DEFAULT_ENDPOINT,
    LAZ_SUFFIX,
    attribution,
    download_tile,
    pick_tile,
    query_candidates,
    summarize,
    validate_bbox,
)

LAZ_FORMAT = LAZ_SUFFIX.lstrip(".")


def descriptor(
    local_path: str,
    bbox: tuple,
    tile: dict,
) -> dict:
    """Build the canonical AssetDescriptor for one downloaded point cloud tile."""
    summary = summarize(tile)
    value = AssetDescriptor(
        asset_id="usgs:3dep:lpc:" + str(summary["source_id"] or os.path.basename(local_path)),
        variants=[
            AssetFileVariant(
                local_path=local_path,
                format=summary["format"] or LAZ_FORMAT,
                preferred=True,
            )
        ],
        attribution=AssetAttribution(**attribution(summary["title"])),
        tags=["point-cloud", "lidar", "usgs", "3dep", "terrain"],
        extra={
            "bbox": list(bbox),
            "source_id": summary["source_id"],
            "title": summary["title"],
            "formats": summary["formats"],
            "publication_date": summary["publication_date"],
            "tile_bounding_box": summary["bounding_box"],
            "preview_graphic_url": summary["preview_graphic_url"],
            "meta_url": summary["meta_url"],
        },
    )
    value.validate()
    return value.to_dict()


def search_candidates(
    south: float,
    west: float,
    north: float,
    east: float,
    endpoint: str = DEFAULT_ENDPOINT,
) -> dict:
    """Return the bounded, deterministic candidate tile list for a bbox."""
    bbox = validate_bbox(south, west, north, east)
    tiles = [summarize(tile) for tile in query_candidates(bbox, endpoint)]
    return {
        "bbox": list(bbox),
        "dataset": "USGS 3DEP Lidar Point Cloud (LPC)",
        "count": len(tiles),
        "candidates": tiles,
    }


@skill_entry
def main(
    south: float,
    west: float,
    north: float,
    east: float,
    output_dir: str,
    source_id: str = "",
    index: int = 0,
    endpoint: str = DEFAULT_ENDPOINT,
    **_: Any,
) -> dict:
    """Download one bounded USGS 3DEP lidar point cloud tile as an AssetDescriptor."""
    try:
        bbox = validate_bbox(south, west, north, east)
        candidates = query_candidates(bbox, endpoint)
        tile = pick_tile(candidates, source_id=source_id, index=index)
        summary = summarize(tile)
        if not summary["download_url"]:
            raise ValueError(
                "Tile %r publishes no LAZ download URL" % (summary["title"] or summary["source_id"])
            )
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.basename(urllib.parse.urlparse(summary["download_url"]).path)
        if not filename:
            filename = "%s.laz" % (summary["source_id"] or "tile")
        local_path = os.path.join(output_dir, filename)
        download_tile(summary["download_url"], local_path)
        return skill_success(
            "USGS 3DEP point cloud tile downloaded",
            files=[local_path],
            size_in_bytes=os.path.getsize(local_path),
            bbox=list(bbox),
            candidate_count=len(candidates),
            asset_descriptor=descriptor(local_path, bbox, tile),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to download USGS 3DEP point cloud tile")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
