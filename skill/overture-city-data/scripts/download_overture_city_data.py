from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from dcc_mcp_core.asset_import import AssetAttribution, AssetDescriptor, AssetFileVariant
from dcc_mcp_core.skill import skill_entry, skill_exception, skill_success


ATTRIBUTION_URL = "https://docs.overturemaps.org/attribution/"
FEATURE_TYPES = {"building", "segment", "connector", "infrastructure", "land", "land_cover", "water"}


def validate_bbox(south: float, west: float, north: float, east: float) -> tuple[float, float, float, float]:
    bbox = tuple(float(value) for value in (south, west, north, east))
    south, west, north, east = bbox
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Bounds must be ordered WGS84 coordinates: south < north and west < east")
    return bbox


def command(feature_type: str, bbox: tuple[float, float, float, float], output_path: str) -> list[str]:
    if feature_type not in FEATURE_TYPES:
        raise ValueError(f"Unsupported Overture city feature type: {feature_type}")
    if not shutil.which("overturemaps"):
        raise RuntimeError("overturemaps is required; install the official Overture Maps Python client")
    south, west, north, east = bbox
    return [
        "overturemaps",
        "download",
        f"--bbox={west},{south},{east},{north}",
        "-f",
        "geojson",
        f"--type={feature_type}",
        "-o",
        output_path,
    ]


def descriptor(feature_type: str, local_path: str, bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    value = AssetDescriptor(
        asset_id=f"overture:city:{feature_type}:" + ",".join(f"{item:.5f}" for item in bbox),
        variants=[AssetFileVariant(local_path=local_path, format="geojson", preferred=True)],
        attribution=AssetAttribution(
            source_url=ATTRIBUTION_URL,
            license_spdx="ODbL-1.0",
            author="Overture Maps Foundation and upstream contributors",
            attribution_text="© OpenStreetMap contributors, Overture Maps Foundation",
        ),
        extra={"bbox": list(bbox), "feature_type": feature_type},
    )
    value.validate()
    return value.to_dict()


@skill_entry
def main(feature_type: str, south: float, west: float, north: float, east: float, output_dir: str, **_: Any) -> dict[str, Any]:
    try:
        bbox = validate_bbox(south, west, north, east)
        target = Path(output_dir).expanduser().resolve() / f"overture-{feature_type}.geojson"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command(feature_type, bbox, str(target)), check=True, capture_output=True, text=True, timeout=600)
        return skill_success(
            "Overture city data downloaded",
            files=[str(target)],
            feature_type=feature_type,
            asset_descriptor=descriptor(feature_type, str(target), bbox),
        )
    except Exception as exc:
        return skill_exception(exc, message="Failed to download Overture city data")


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
