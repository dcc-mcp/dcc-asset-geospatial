from __future__ import annotations

from typing import Any

from dcc_mcp_core.asset_import import AssetAttribution, AssetDescriptor, AssetFileVariant
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success

from _osm import COPYRIGHT_URL, DEFAULT_ENDPOINT, build_query, request_overpass, to_geojson, validate_bbox, write_geojson


def descriptor(local_path: str, bbox: tuple[float, float, float, float], layers: list[str], feature_count: int) -> dict[str, Any]:
    value = AssetDescriptor(
        asset_id="openstreetmap:city:" + ",".join(f"{item:.5f}" for item in bbox),
        variants=[AssetFileVariant(local_path=local_path, format="geojson", preferred=True)],
        attribution=AssetAttribution(
            source_url=COPYRIGHT_URL,
            license_spdx="ODbL-1.0",
            author="OpenStreetMap contributors",
            attribution_text="© OpenStreetMap contributors",
        ),
        extra={"bbox": list(bbox), "layers": layers, "feature_count": feature_count},
    )
    value.validate()
    return value.to_dict()


@skill_entry
def main(
    south: float,
    west: float,
    north: float,
    east: float,
    output_dir: str,
    layers: list[str] | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    **_: Any,
) -> dict[str, Any]:
    try:
        bbox = validate_bbox(south, west, north, east)
        selected = layers or ["buildings", "roads", "railways", "water", "landuse"]
        query = build_query(bbox, selected)
        geojson = to_geojson(request_overpass(endpoint, query))
        local_path = write_geojson(geojson, output_dir)
        return skill_success(
            "OpenStreetMap city data downloaded",
            files=[local_path],
            feature_count=len(geojson["features"]),
            layers=selected,
            asset_descriptor=descriptor(local_path, bbox, selected, len(geojson["features"])),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to download OpenStreetMap city data")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
