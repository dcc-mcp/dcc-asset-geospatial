---
name: overture-city-data
description: Download bounded Overture Maps city features as licensed GeoJSON for procedural city workflows.
license: MIT
compatibility: "dcc-mcp-core 0.19+, Python 3.10+"
metadata:
  dcc-mcp:
    version: v0.1.0
    dcc: python
    layer: domain
    tags: [asset, geospatial, overture, city, pcg, geojson]
    search-hint: "Overture city data, building footprints, roads, land cover, Houdini city PCG, Blender city generator"
    produces: [asset_descriptor]
    tools: tools.yaml
---

# Overture City Data

Use this skill for bounded city-scale extracts from the current Overture Maps release. Install the
official `overturemaps` client first. The skill supports the ODbL city themes most useful for PCG:
buildings, transport segments and connectors, infrastructure, land, land cover, and water.

The result is GeoJSON. Projection, geometry cleanup, extrusion, and scene import remain downstream
DCC responsibilities. Retain Overture and upstream attribution from the returned descriptor.
