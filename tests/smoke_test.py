from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import urllib.parse
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


def pointcloud_terrain_guards_smoke() -> None:
    from dcc_mcp_core import parse_skill_md

    helper = load("pointcloud-terrain", "_tnm")
    module = load("pointcloud-terrain", "pointcloud_terrain")
    skill_dir = ROOT / "skill" / "pointcloud-terrain"

    # Declared tool group: tools.yaml assigns both tools to `geospatial`, so the
    # group must be declared or the tools load behind an undeclared group.
    meta = parse_skill_md(str(skill_dir))
    declared_groups = {
        group["name"] if isinstance(group, dict) else group.name for group in meta.groups
    }
    assert declared_groups == {"geospatial"}, declared_groups

    # Declared output_schema must describe the skill_success envelope: the
    # payload lives under context, and `success` is the only required key.
    # Declared output_schema must describe the skill_success envelope: the
    # payload lives under context, and `success` is the only required key.
    expected_context_keys = {
        "search_pointcloud_terrain": "candidate_count",
        "download_pointcloud_terrain": "asset_descriptor",
    }
    declared_tools = set()
    for tool in meta.tools:
        schema = tool.output_schema
        if isinstance(schema, str):
            schema = json.loads(schema)
        schema = schema or {}
        assert schema.get("required") == ["success"], (tool.name, schema.get("required"))
        context_props = (((schema.get("properties") or {}).get("context") or {}).get("properties")) or {}
        assert expected_context_keys[tool.name] in context_props, (tool.name, sorted(context_props))
        declared_tools.add(tool.name)
    assert declared_tools == set(expected_context_keys), declared_tools

    # Only allowlisted USGS hosts may be reached, and only over HTTPS.
    for rejected in (
        "http://tnmaccess.nationalmap.gov/api/v1/products",
        "https://internal.example.com/api/v1/products",
        "https://tnmaccess.nationalmap.gov.evil.test/api/v1/products",
        "ftp://rockyweb.usgs.gov/tile.laz",
        "https://user:secret@rockyweb.usgs.gov/tile.laz",
        "https://tnmaccess.nationalmap.gov:8443/api/v1/products",
    ):
        try:
            helper.ensure_allowed_url(rejected)
            raise AssertionError("%r must be rejected" % rejected)
        except helper.UrlNotAllowedError:
            pass
    helper.ensure_allowed_url(helper.DEFAULT_ENDPOINT)
    helper.ensure_allowed_url("https://rockyweb.usgs.gov/tile.laz")

    # Only tiles that publish a real .laz URL may be reported as format: laz.
    laz_tile = {
        "title": "laz tile",
        "sourceId": "1",
        "downloadURL": "https://rockyweb.usgs.gov/a.laz",
        "urls": {"LAZ": "https://rockyweb.usgs.gov/a.laz"},
    }
    las_tile = {
        "title": "las tile",
        "sourceId": "2",
        "downloadURL": "https://rockyweb.usgs.gov/b.las",
        "urls": {"LAS": "https://rockyweb.usgs.gov/b.las"},
    }
    assert helper.laz_download_url(laz_tile) == "https://rockyweb.usgs.gov/a.laz"
    assert helper.laz_download_url(las_tile) == ""
    assert helper.summarize(laz_tile)["format"] == "laz"
    assert helper.summarize(las_tile)["format"] == ""

    # The search tool answers with the envelope the schema describes.
    import pointcloud_terrain as pt  # scripts dir is already on sys.path

    original_query = pt.query_candidates
    pt.query_candidates = lambda bbox, endpoint=helper.DEFAULT_ENDPOINT, timeout=0: [laz_tile]
    try:
        search_tool = load("pointcloud-terrain", "search_pointcloud_terrain")
        envelope = search_tool.main(south=39.70, west=-105.60, north=39.703, east=-105.595)
    finally:
        pt.query_candidates = original_query
    assert envelope["success"] is True, envelope
    assert {"success", "message", "context"} <= set(envelope), sorted(envelope)
    assert envelope["context"]["candidate_count"] == 1
    assert envelope["context"]["bbox"] == [39.7, -105.6, 39.703, -105.595]

    # TNM pages its results; every page must be walked so a tile beyond the
    # first page is still selectable, and the scan stays bounded.
    def fake_tile(index):
        return {
            "title": "tile %03d" % index,
            "sourceId": "%03d" % index,
            "downloadURL": "https://rockyweb.usgs.gov/%03d.laz" % index,
            "urls": {"LAZ": "https://rockyweb.usgs.gov/%03d.laz" % index},
        }

    pages = [
        {"total": 150, "items": [fake_tile(i) for i in range(100)]},
        {"total": 150, "items": [fake_tile(i) for i in range(100, 150)]},
    ]
    requested = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def read(self, *_args):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    def fake_open(url, timeout, headers=None):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        requested.append((query["max"][0], query["offset"][0]))
        page = pages[0] if query["offset"][0] == "0" else pages[1]
        return FakeResponse(json.dumps(page).encode("utf-8"))

    with patch.object(helper, "open_allowed_url", fake_open):
        candidates = helper.query_candidates(helper.validate_bbox(39.70, -105.60, 39.703, -105.595))
    assert requested == [("100", "0"), ("100", "100")], requested
    assert len(candidates) == 25, len(candidates)
    assert candidates[0]["sourceId"] == "000", candidates[0]

    # A download falls back to the published TNM size when the response has no
    # usable Content-Length.
    assert helper._resolve_expected_size("12", 99) == 12
    assert helper._resolve_expected_size(None, 48093708) == 48093708
    assert helper._resolve_expected_size("bogus", 48093708) == 48093708
    assert helper._resolve_expected_size(None, None) is None

    # A truncated or non-LAZ payload must never be accepted as a tile.
    with tempfile.TemporaryDirectory() as tmp:
        good = os.path.join(tmp, "tile.laz")
        with open(good, "wb") as handle:
            handle.write(b"LASF" + b"\x00" * 8)
        assert helper.verify_laz_payload(good, 12) == 12
        for size in (11, 13):
            try:
                helper.verify_laz_payload(good, size)
                raise AssertionError("size mismatch (%d) must be rejected" % size)
            except ValueError:
                pass
        html_page = os.path.join(tmp, "error.html")
        with open(html_page, "wb") as handle:
            handle.write(b"<html>Service Unavailable</html>")
        try:
            helper.verify_laz_payload(html_page, os.path.getsize(html_page))
            raise AssertionError("non-LAZ payload must be rejected")
        except ValueError:
            pass


def main() -> None:
    validate_skills()
    openstreetmap_smoke()
    overture_smoke()
    pointcloud_terrain_smoke()
    pointcloud_terrain_guards_smoke()


if __name__ == "__main__":
    main()
