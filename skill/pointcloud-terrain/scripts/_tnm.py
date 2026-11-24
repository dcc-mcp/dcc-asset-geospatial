from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Optional


DEFAULT_ENDPOINT = "https://tnmaccess.nationalmap.gov/api/v1/products"
DATASET = "Lidar Point Cloud (LPC)"
USER_AGENT = "dcc-mcp-pointcloud-terrain/0.1"

# Both tools take a caller-supplied ``endpoint``, so every request — including
# each redirect hop — is pinned to the public USGS hosts that publish TNM
# metadata and 3DEP tiles. Without this pin a caller could aim the skill at an
# internal HTTPS service and use it as a GET proxy.
ALLOWED_HOSTS = ("tnmaccess.nationalmap.gov", "rockyweb.usgs.gov")
ALLOWED_PORTS = (443,)

# Only LAZ payloads are accepted: the LASF signature is why a variant can be
# published as ``format: laz`` at all.
LAZ_MAGIC = b"LASF"
LAZ_SUFFIX = ".laz"
TEMP_SUFFIX = ".part"

# USGS 3DEP tiles are large, so a single query is capped to keep the candidate
# list bounded and the download predictable.
MAX_BBOX_AREA_SQ_DEG = 0.04
MAX_CANDIDATES = 25

# TNM pages its product results: ``max`` must be a multiple of 5 and at most
# 1000. A query walks pages until the reported ``total`` is covered or the scan
# cap is reached, so a candidate on a later page is never silently dropped.
PAGE_SIZE = 100
MAX_SCANNED_ITEMS = 500

LPC_PUBLIC_DOMAIN = (
    "Unless otherwise noted, data and publications on the USGS Science Data Catalog are "
    "in the public domain and may be used without permission, though USGS asks for credit."
)
SOURCE_URL = "https://www.usgs.gov/3d-elevation-program"
LICENSE_SPDX = "USGS-PD"


class BoundsError(ValueError):
    """Raised when a requested bounding box is unusable for a bounded query."""


class UrlNotAllowedError(ValueError):
    """Raised when a URL leaves the pinned USGS host allowlist."""


def ensure_allowed_url(url: str) -> str:
    """Validate that ``url`` points at an allowlisted USGS host over HTTPS."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise UrlNotAllowedError("USGS requests must use HTTPS, got %r" % (parsed.scheme or url))
    if parsed.username or parsed.password:
        raise UrlNotAllowedError("URL credentials are not allowed: %r" % url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise UrlNotAllowedError(
            "Host %r is not an allowed USGS data host (allowed: %s)"
            % (host, ", ".join(ALLOWED_HOSTS))
        )
    if parsed.port is not None and parsed.port not in ALLOWED_PORTS:
        raise UrlNotAllowedError("Port %r is not allowed for USGS requests" % parsed.port)
    return url


class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-run the allowlist check on every redirect hop before following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ensure_allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_allowed_url(url: str, timeout: float, headers: dict = None):
    """Open ``url`` with the allowlist enforced on the request and every hop."""
    ensure_allowed_url(url)
    opener = urllib.request.build_opener(_AllowlistRedirectHandler())
    request = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    return opener.open(request, timeout=timeout)


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
    page_size: int = None,
    offset: int = None,
) -> str:
    """Build a bounded TNM products query URL for ``bbox``."""
    south, west, north, east = bbox
    params = [
        ("datasets", dataset),
        ("bbox", "%s,%s,%s,%s" % (west, south, east, north)),
    ]
    if page_size is not None:
        params.append(("max", str(page_size)))
    if offset is not None:
        params.append(("offset", str(offset)))
    return endpoint + "?" + urllib.parse.urlencode(params)


def query_candidates(bbox: tuple, endpoint: str = DEFAULT_ENDPOINT, timeout: float = 120.0) -> list:
    """Return the bounded, deterministic LAZ candidate list for ``bbox``.

    Only tiles that publish a real ``.laz`` URL are returned, so a chosen tile
    can always be reported as ``format: laz`` without guessing. Every result
    page is walked up to ``MAX_SCANNED_ITEMS`` so a tile on a later page is not
    dropped, and the surviving candidates are sorted by ``(title, sourceId)``
    so repeated queries for the same bbox return the same ordering regardless
    of upstream response order.
    """
    endpoint = ensure_allowed_url(endpoint)
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    items = []
    offset = 0
    while len(items) < MAX_SCANNED_ITEMS:
        url = build_query_url(bbox, endpoint, page_size=PAGE_SIZE, offset=offset)
        with open_allowed_url(url, timeout, headers=request_headers) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page = payload.get("items") or []
        items.extend(page)
        offset += len(page)
        total = payload.get("total")
        if not page or len(page) < PAGE_SIZE:
            break
        if isinstance(total, int) and offset >= min(total, MAX_SCANNED_ITEMS):
            break
    return sorted(
        (item for item in items if laz_download_url(item)),
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


def laz_download_url(tile: dict) -> str:
    """Return the tile's LAZ download URL, or ``""`` when it publishes none.

    A tile may advertise LAS, GeoPackage, or other products as well. Only a URL
    whose path really ends in ``.laz`` may be published as ``format: laz``.
    """
    urls = tile.get("urls") or {}
    for candidate in (urls.get("LAZ"), tile.get("downloadURL")):
        if not candidate:
            continue
        if urllib.parse.urlparse(str(candidate)).path.lower().endswith(LAZ_SUFFIX):
            return str(candidate)
    return ""


def summarize(tile: dict) -> dict:
    """Reduce one TNM item to the fields a caller needs to choose and download."""
    box = tile.get("boundingBox") or {}
    urls = tile.get("urls") or {}
    download_url = laz_download_url(tile)
    return {
        "title": tile.get("title") or "",
        "source_id": tile.get("sourceId") or "",
        "format": LAZ_SUFFIX.lstrip(".") if download_url else "",
        "size_in_bytes": tile.get("sizeInBytes"),
        "publication_date": tile.get("publicationDate") or "",
        "download_url": download_url,
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


def verify_laz_payload(path: str, expected_size: int = None) -> int:
    """Verify a downloaded payload is a complete LAZ file and return its size."""
    actual_size = os.path.getsize(path)
    if expected_size is not None and actual_size != expected_size:
        raise ValueError(
            "Truncated download: expected %d bytes, received %d" % (expected_size, actual_size)
        )
    with open(path, "rb") as handle:
        magic = handle.read(len(LAZ_MAGIC))
    if magic != LAZ_MAGIC:
        raise ValueError("Downloaded payload is not a LASF/LAZ file")
    return actual_size


def download_tile(
    url: str,
    destination: str,
    chunk_size: int = 1 << 20,
    timeout: float = 600.0,
    expected_size: Any = None,
) -> str:
    """Stream an allowlisted LAZ tile to ``destination`` and return its path.

    The payload is written to a sidecar ``.part`` file and only moved into place
    after the byte count matches ``Content-Length`` — or, when the response does
    not report one, the size published by TNM — and the LAZ signature is
    present. An early EOF or an HTML error page therefore fails instead of being
    published as a successful tile.
    """
    ensure_allowed_url(url)
    temp_path = destination + TEMP_SUFFIX
    try:
        with open_allowed_url(url, timeout) as response:
            resolved_size = _resolve_expected_size(
                response.headers.get("Content-Length"), expected_size
            )
            with open(temp_path, "wb") as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
        verify_laz_payload(temp_path, resolved_size)
        os.replace(temp_path, destination)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    return destination


def _resolve_expected_size(content_length: Any, fallback: Any) -> Optional[int]:
    """Prefer the response ``Content-Length``, falling back to the TNM size."""
    parsed = _parse_content_length(content_length)
    if parsed is not None:
        return parsed
    return _parse_content_length(fallback)


def _parse_content_length(value: Any) -> Optional[int]:
    """Return ``Content-Length`` as an int, or ``None`` when absent or invalid."""
    if value is None:
        return None
    try:
        length = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return length if length >= 0 else None


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
