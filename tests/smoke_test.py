from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(skill: str, name: str):
    scripts = ROOT / "skill" / skill / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(f"{skill}_{name}", scripts / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def validate_skills() -> None:
    from dcc_mcp_core import validate_skill

    for name in ("openstreetmap-city-data", "overture-city-data"):
        report = validate_skill(str(ROOT / "skill" / name))
        assert not report.has_errors, report


def openstreetmap_smoke() -> None:
    helper = load("openstreetmap-city-data", "_osm")
    bbox = helper.validate_bbox(40.70, -74.02, 40.71, -74.01)
    query = helper.build_query(bbox, ["buildings", "roads"])
    assert 'way["building"]' in query and 'way["highway"]' in query
    value = helper.to_geojson(
        {
            "elements": [
                {"type": "way", "id": 1, "tags": {"building": "yes"}, "geometry": [{"lat": 1, "lon": 2}, {"lat": 1, "lon": 3}, {"lat": 2, "lon": 3}, {"lat": 1, "lon": 2}]},
                {"type": "way", "id": 2, "tags": {"highway": "residential"}, "geometry": [{"lat": 1, "lon": 2}, {"lat": 2, "lon": 3}]},
            ]
        }
    )
    assert value["features"][0]["geometry"]["type"] == "Polygon"
    assert value["features"][1]["geometry"]["type"] == "LineString"
    assert value["license"] == "ODbL-1.0"


def overture_smoke() -> None:
    module = load("overture-city-data", "download_overture_city_data")
    bbox = module.validate_bbox(40.70, -74.02, 40.71, -74.01)
    with patch.object(module.shutil, "which", return_value="/bin/overturemaps"):
        value = module.command("building", bbox, "/tmp/buildings.geojson")
    assert value[2] == "--bbox=-74.02,40.7,-74.01,40.71"
    descriptor = module.descriptor("building", "/tmp/buildings.geojson", bbox)
    assert descriptor["attribution"]["license_spdx"] == "ODbL-1.0"


def main() -> None:
    validate_skills()
    openstreetmap_smoke()
    overture_smoke()


if __name__ == "__main__":
    main()
