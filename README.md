# DCC-MCP Geospatial Assets

<p align="center">
  <img src="docs/assets/dcc-asset-geospatial.svg" alt="DCC-MCP · GEOSPATIAL-ASSETS" width="600">
</p>

## Agent workflow

AI agents should use installed package skills through the shared gateway. IDE
users may continue to use the MCP endpoint.

```bash
dcc-mcp-cli dcc-types
dcc-mcp-cli list
dcc-mcp-cli search --query "<task>" --dcc-type <host>
dcc-mcp-cli describe <tool-slug>
dcc-mcp-cli call <tool-slug> --json '{"key":"value"}'
```

If the package skill is not active, call
`dcc-mcp-cli load-skill <skill-name> --dcc-type <host>`. After the task,
query `dcc-mcp-cli stats --range 24h --session-id <task-id>` and pass only
bounded evidence to the `review_skill_improvement` prompt from
`dcc-mcp-skills-creator`.


DCC-neutral providers for downloading city-scale geospatial data for Houdini, Blender, Unreal,
and other procedural content workflows.

- `openstreetmap-city-data` queries a bounded OpenStreetMap area through Overpass and writes
  buildings, roads, railways, water, and land use to GeoJSON.
- `overture-city-data` wraps the official Overture Maps client for bounded GeoJSON extracts of
  buildings, transportation, infrastructure, land, land cover, and water.

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

## Validate

```bash
python tests/smoke_test.py
```
