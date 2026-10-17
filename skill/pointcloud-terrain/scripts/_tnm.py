from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_ENDPOINT = "https://tnmaccess.nationalmap.gov/api/v1/products"
DATASET = "Lidar Point Cloud (LPC)"
USER_AGENT = "dcc-mcp-pointcloud-terrain/0.1"

# USGS 3DEP tiles are large, so a single query is capped to keep the candidate
# list bounded and the download predictable.
MAX_BBOX_AREA_SQ_DEG = 0.04
MAX_CANDIDATES = 25

LPC_PUBLIC_DOMAIN = (
    "Unless otherwise noted, data and publications on the USGS Science Data Catalog are "
    "in the public domain and may be used without permission, though USGS asks for credit."
)
SOURCE_URL = "https://www.usgs.gov/3d-elevation-program"
LICENSE_SPDX = "USGS-PD"


class BoundsError(ValueError):
    """Raised when a requested bounding box is unusable for a bounded query."""


def validate_bbox(south: float, west: float, north: float, east: float) -> tuple:
    """Validate a WGS84 bounding box and return it as ``(south, west, north, east)``."""
    south, west, north, east = (float(value) for value in (south, west, north, east))
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise BoundsError("Bounds must be ordered WGS84 coordinates: south < north and west < east")
    if (north - south) * (east - west) > MAX_BBOX_AREA_SQ_DEG:
        raise BoundsError(
            "Requested area exceeds the %.2f square-degree bounded query limit" % MAX_BBOX_AREA_SQ_DEG
        )
    return (south, west, north, east)


def build_query_url(
    bbox: tuple,
    endpoint: str = DEFAULT_ENDPOINT,
    dataset: str = DATASET,
) -> str:
    """Build a bounded TNM products query URL for ``bbox``."""
    south, west, north, east = bbox
    params = [
        ("datasets", dataset),
        ("bbox", "%s,%s,%s,%s" % (west, south, east, north)),
    ]
    return endpoint + "?" + urllib.parse.urlencode(params)


def query_candidates(bbox: tuple, endpoint: str = DEFAULT_ENDPOINT, timeout: float = 120.0) -> list:
    """Return the bounded, deterministic candidate tile list for ``bbox``.

    The list is sorted by ``(title, sourceId)`` so repeated queries for the same
    bbox return the same ordering regardless of upstream response order.
    """
    if urllib.parse.urlparse(endpoint).scheme != "https":
        raise ValueError("TNM endpoint must use HTTPS")
    request = urllib.request.Request(
        build_query_url(bbox, endpoint),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload.get("items") or []
    return sorted(
        items,
        key=lambda item: (str(item.get("title") or ""), str(item.get("sourceId") or "")),
    )[:MAX_CANDIDATES]


def tile_intersects_bbox(tile: dict, bbox: tuple) -> bool:
    """Return True when a tile's published bounding box overlaps ``bbox``."""
    south, west, north, east = bbox
    box = tile.get("boundingBox") or {}
    try:
        min_x = float(box.get("minX"))
        max_x = float(box.get("maxX"))
        min_y = float(box.get("minY"))
        max_y = float(box.get("maxY"))
    except (TypeError, ValueError):
        return False
    return not (max_x < west or min_x > east or max_y < south or min_y > north)


def summarize(tile: dict) -> dict:
    """Reduce one TNM item to the fields a caller needs to choose and download."""
    box = tile.get("boundingBox") or {}
    urls = tile.get("urls") or {}
    return {
        "title": tile.get("title") or "",
        "source_id": tile.get("sourceId") or "",
        "format": tile.get("format") or "",
        "size_in_bytes": tile.get("sizeInBytes"),
        "publication_date": tile.get("publicationDate") or "",
        "download_url": tile.get("downloadURL") or urls.get("LAZ") or "",
        "formats": sorted(str(key) for key in urls),
        "bounding_box": {
            "min_x": box.get("minX"),
            "min_y": box.get("minY"),
            "max_x": box.get("maxX"),
            "max_y": box.get("maxY"),
        },
        "preview_graphic_url": tile.get("previewGraphicURL") or "",
        "meta_url": tile.get("metaUrl") or "",
    }


def pick_tile(candidates: list, source_id: str = "", index: int = 0) -> dict:
    """Select one candidate tile by ``source_id``, or by position when unset."""
    if not candidates:
        raise ValueError("No point cloud tiles are published for this bounding box")
    if source_id:
        for tile in candidates:
            if str(tile.get("sourceId") or "") == source_id:
                return tile
        raise ValueError("source_id %r is not in the candidate list for this bounding box" % source_id)
    if index < 0 or index >= len(candidates):
        raise ValueError(
            "index %d is out of range for %d candidates" % (index, len(candidates))
        )
    return candidates[index]


def download_tile(url: str, destination: str, chunk_size: int = 1 << 20, timeout: float = 600.0) -> str:
    """Stream ``url`` to ``destination`` and return the written path."""
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError("Tile download URL must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with open(destination, "wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
    return destination


def attribution(title: str = "") -> dict:
    """Build the USGS 3DEP attribution payload for a downloaded tile."""
    return {
        "source_url": SOURCE_URL,
        "license_spdx": LICENSE_SPDX,
        "license_text": LPC_PUBLIC_DOMAIN,
        "author": "U.S. Geological Survey (USGS)",
        "title": title or "USGS 3DEP lidar point cloud",
        "attribution_text": "U.S. Geological Survey (USGS) 3D Elevation Program (3DEP)",
    }


def attribution_to_dict(value: Any) -> dict:
    """Normalize an attribution mapping to a plain dict."""
    return dict(value)
