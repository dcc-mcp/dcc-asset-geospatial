---
name: pointcloud-terrain
description: Download bounded USGS 3DEP lidar point cloud tiles as attributed LAZ for terrain workflows.
license: MIT
compatibility: "dcc-mcp-core 0.19+, Python 3.10+"
metadata:
  dcc-mcp:
    version: v0.1.0
    dcc: python
    layer: domain
    tags: [asset, geospatial, point-cloud, lidar, usgs, 3dep, terrain]
    search-hint: "USGS 3DEP lidar point cloud, LAZ terrain tiles, Houdini terrain, Unreal landscape point cloud"
    produces: [asset_descriptor]
    tools: tools.yaml
---

# Point Cloud Terrain

Use this skill to fetch real-world lidar point clouds as `LAZ` tiles for terrain, landscape, and
procedural scattering work. Supply WGS84 bounds and the skill returns the bounded candidate tiles
published by the USGS 3D Elevation Program (3DEP), then downloads the one you pick.

Two tools are provided. `search_pointcloud_terrain` lists candidates so you can choose a tile and
see its size before committing to a download. `download_pointcloud_terrain` performs the download
and returns a validated `AssetDescriptor` carrying the source URL, license, and attribution.

## Coverage and limits

USGS 3DEP coverage is the contiguous United States, Alaska, Hawaii, and US territories. Bounding
boxes elsewhere return an empty candidate list; this is a coverage limit, not a query error.

Queries are capped at 0.04 square degrees and return at most 25 candidates, so a bbox always
produces a bounded, deterministic list rather than an unbounded crawl. For larger areas, call the
skill once per tile.

No API key is required. Both tools work keyless against the public TNM API.

Individual 3DEP tiles are large, commonly 40-200 MB. `download_pointcloud_terrain` is not
idempotent: each call writes the tile again.

## Licensing and attribution

USGS data and publications are, unless otherwise noted, in the public domain and may be used
without permission. USGS asks for credit. Every returned `AssetDescriptor` carries
`license_spdx: USGS-PD`, the public-domain statement, and an attribution string naming the U.S.
Geological Survey 3D Elevation Program. Keep the attribution with the data.

## Scope

This skill downloads point cloud data only. Decimation, reprojection, DEM raster generation, mesh
conversion, and import into a DCC scene belong to the target DCC skill.
