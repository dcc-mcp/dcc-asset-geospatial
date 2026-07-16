---
name: openstreetmap-city-data
description: Download bounded OpenStreetMap city features as attributed GeoJSON for procedural city workflows.
license: MIT
compatibility: "dcc-mcp-core 0.19+, Python 3.10+"
metadata:
  dcc-mcp:
    version: v0.1.0
    dcc: python
    layer: domain
    tags: [asset, geospatial, openstreetmap, city, pcg, geojson]
    search-hint: "OpenStreetMap city data, OSM buildings, roads, Houdini city PCG, Blender city generator"
    produces: [asset_descriptor]
    tools: tools.yaml
---

# OpenStreetMap City Data

Use this skill for a city district or other bounded area. Supply WGS84 bounds and select only the
layers needed. The result is GeoJSON suitable for downstream reprojection and procedural modeling.

Queries are deliberately capped at 0.04 square degrees to protect shared Overpass services. For
larger or repeated extracts, use `overture-city-data` or a regional OpenStreetMap extract instead.

The first version exports way geometry. It does not reconstruct complex multipolygon relations.

OpenStreetMap data is ODbL 1.0. Public use requires attribution to OpenStreetMap contributors, and
published derivative databases may carry share-alike obligations. Keep the returned attribution.
