from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
LAYER_FILTERS = {
    "buildings": ['way["building"]'],
    "roads": ['way["highway"]'],
    "railways": ['way["railway"]'],
    "water": ['way["natural"="water"]', 'way["waterway"]', 'way["water"]'],
    "landuse": ['way["landuse"]'],
}


def validate_bbox(south: float, west: float, north: float, east: float) -> tuple[float, float, float, float]:
    bbox = tuple(float(value) for value in (south, west, north, east))
    south, west, north, east = bbox
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Bounds must be ordered WGS84 coordinates: south < north and west < east")
    if (north - south) * (east - west) > 0.04:
        raise ValueError("Requested area exceeds the 0.04 square-degree Overpass safety limit")
    return bbox


def build_query(bbox: tuple[float, float, float, float], layers: list[str]) -> str:
    if not layers:
        raise ValueError("At least one layer is required")
    unknown = sorted(set(layers) - set(LAYER_FILTERS))
    if unknown:
        raise ValueError(f"Unsupported OpenStreetMap layers: {', '.join(unknown)}")
    box = ",".join(f"{value:.7f}" for value in bbox)
    statements = [f"  {item}({box});" for layer in layers for item in LAYER_FILTERS[layer]]
    return "[out:json][timeout:120];\n(\n" + "\n".join(statements) + "\n);\nout geom;"


def request_overpass(endpoint: str, query: str) -> dict[str, Any]:
    if urllib.parse.urlparse(endpoint).scheme != "https":
        raise ValueError("Overpass endpoint must use HTTPS")
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"User-Agent": "dcc-mcp-geospatial/0.1", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def to_geojson(data: dict[str, Any]) -> dict[str, Any]:
    # ponytail: ways cover district PCG; add relation ring stitching when multipolygon completeness is required.
    features = []
    for element in data.get("elements") or []:
        geometry = element.get("geometry") or []
        coordinates = [[point["lon"], point["lat"]] for point in geometry if "lon" in point and "lat" in point]
        if len(coordinates) < 2:
            continue
        tags = dict(element.get("tags") or {})
        closed = len(coordinates) >= 4 and coordinates[0] == coordinates[-1]
        linear = any(key in tags for key in ("highway", "railway", "barrier")) or (
            "waterway" in tags and tags["waterway"] not in {"riverbank", "dock"}
        )
        shape = {"type": "Polygon", "coordinates": [coordinates]} if closed and not linear and tags.get("area") != "no" else {"type": "LineString", "coordinates": coordinates}
        features.append(
            {
                "type": "Feature",
                "id": f"{element.get('type', 'way')}/{element.get('id')}",
                "properties": {"osm_id": element.get("id"), "osm_type": element.get("type"), **tags},
                "geometry": shape,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "attribution": "© OpenStreetMap contributors",
        "license": "ODbL-1.0",
        "source": COPYRIGHT_URL,
    }


def write_geojson(value: dict[str, Any], output_dir: str) -> str:
    target = Path(output_dir).expanduser().resolve() / "openstreetmap-city.geojson"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return str(target)
