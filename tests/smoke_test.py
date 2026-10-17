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

    for name in ("openstreetmap-city-data", "overture-city-data", "pointcloud-terrain"):
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


def pointcloud_terrain_smoke() -> None:
    from dcc_mcp_core.asset_import import AssetDescriptor

    helper = load("pointcloud-terrain", "_tnm")
    module = load("pointcloud-terrain", "pointcloud_terrain")

    bbox = helper.validate_bbox(39.70, -105.60, 39.703, -105.595)
    url = helper.build_query_url(bbox)
    assert "datasets=Lidar+Point+Cloud" in url
    assert "bbox=-105.6%2C39.7%2C-105.595%2C39.703" in url

    # Bounded: an oversized bbox must be rejected rather than crawled.
    try:
        helper.validate_bbox(39.0, -106.0, 40.0, -105.0)
        raise AssertionError("oversized bbox must be rejected")
    except helper.BoundsError:
        pass

    # Deterministic: candidates are ordered by (title, sourceId), so the same
    # bbox always yields the same list regardless of upstream response order.
    tile_a = {"title": "B", "sourceId": "2", "boundingBox": {}, "urls": {}}
    tile_b = {"title": "A", "sourceId": "1", "boundingBox": {}, "urls": {}}
    ordered = sorted([tile_a, tile_b], key=lambda t: (t["title"], t["sourceId"]))
    assert [t["sourceId"] for t in ordered] == ["1", "2"]

    # Real fixture: the tile downloaded from USGS 3DEP during de-risking.
    tile = {
        "title": "USGS Lidar Point Cloud CO_Central_and_WesternCO_2016_A16 LD29701680",
        "sourceId": "63414231d34e342aee07bd46",
        "format": "LAZ",
        "sizeInBytes": 48093708,
        "publicationDate": "2022-08-19",
        "downloadURL": "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CO_Central_and_WesternCO_2016_A16/CO_Central_Western_2016/LAZ/USGS_LPC_CO_Central_and_WesternCO_2016_A16_LD29701680.laz",
        "urls": {"LAZ": "https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/LPC/Projects/CO_Central_and_WesternCO_2016_A16/CO_Central_Western_2016/LAZ/USGS_LPC_CO_Central_and_WesternCO_2016_A16_LD29701680.laz"},
        "boundingBox": {"minX": -105.6066295022476, "maxX": -105.59595529778525, "minY": 39.70035218185938, "maxY": 39.70859713398212},
        "previewGraphicURL": "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/LPC/Projects/CO_Central_and_WesternCO_2016_A16/CO_Central_Western_2016/browse/USGS_LPC_CO_Central_and_WesternCO_2016_A16_LD29701680.jpg",
        "metaUrl": "https://www.sciencebase.gov/catalog/item/63414231d34e342aee07bd46",
    }
    descriptor = module.descriptor("/data/tile.laz", bbox, tile)
    AssetDescriptor.from_dict(descriptor).validate()
    assert descriptor["asset_id"] == "usgs:3dep:lpc:63414231d34e342aee07bd46"
    assert descriptor["variants"][0]["format"] == "laz"
    assert descriptor["attribution"]["license_spdx"] == "USGS-PD"
    assert descriptor["attribution"]["author"] == "U.S. Geological Survey (USGS)"
    assert descriptor["attribution"]["source_url"] == "https://www.usgs.gov/3d-elevation-program"


def main() -> None:
    validate_skills()
    openstreetmap_smoke()
    overture_smoke()
    pointcloud_terrain_smoke()


if __name__ == "__main__":
    main()
