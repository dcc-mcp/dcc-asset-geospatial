# DCC-MCP Geospatial Assets

DCC-neutral providers for downloading city-scale geospatial data for Houdini, Blender, Unreal,
and other procedural content workflows.

- `openstreetmap-city-data` queries a bounded OpenStreetMap area through Overpass and writes
  buildings, roads, railways, water, and land use to GeoJSON.
- `overture-city-data` wraps the official Overture Maps client for bounded GeoJSON extracts of
  buildings, transportation, infrastructure, land, land cover, and water.
- `pointcloud-terrain` lists and downloads bounded USGS 3DEP lidar point cloud tiles as attributed
  `LAZ` for terrain, landscape, and scattering work.

Every download returns a validated `AssetDescriptor` with the source URL, data license, required
attribution, requested bounds, and local file. These skills download data only; projection,
extrusion, terrain conformation, and scene import belong to the target DCC skill.

## Showcases

### OpenStreetMap city data

![Bounded map layers converted to attributed GeoJSON and a procedural city](docs/images/openstreetmap-city-data-showcase.webp)

### Overture city data

![Global city themes extracted by bounding box for a procedural city](docs/images/overture-city-data-showcase.webp)

These are original workflow illustrations; no map tiles, provider logos, or product interfaces are
reproduced.

See [geospatial data source coverage](docs/data-source-candidates.md) for terrain, land-cover, bulk
OpenStreetMap, and regional follow-up providers.

### Point cloud coverage

`pointcloud-terrain` uses the USGS 3D Elevation Program, which is keyless and covers the contiguous
United States, Alaska, Hawaii, and US territories. Bounding boxes outside that coverage return an
empty candidate list. Each query is capped at 0.04 square degrees and at most 25 candidates, and
results are ordered by tile title and source id so the same bounds always return the same list.

USGS data is public domain unless otherwise noted, and USGS asks for credit. Every returned
`AssetDescriptor` carries `USGS-PD` and a USGS 3DEP attribution string.

## Validate

```bash
python tests/smoke_test.py
```
