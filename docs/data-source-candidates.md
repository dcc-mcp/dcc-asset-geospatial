# Geospatial data source coverage

## Implemented

| Source | PCG value | Access | Data license |
| --- | --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Buildings, roads, railways, water, and land use for district-scale generation | Bounded Overpass query | ODbL 1.0 |
| [Overture Maps](https://docs.overturemaps.org/getting-data/overturemaps-py/) | Global building, transportation, infrastructure, land-cover, and water extracts | Official CLI, bounded GeoJSON | ODbL for the supported city themes |

## Good follow-up skills

| Source | PCG value | Decision |
| --- | --- | --- |
| [Natural Earth](https://www.naturalearthdata.com/about/) | Public-domain coastlines, rivers, boundaries, and regional context | Add when world-scale environment blocking is needed; it is too generalized for street-scale cities. |
| [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | Public-domain DEM and lidar for terrain conformation | Strong next provider for United States projects; label the regional coverage clearly. |
| [ESA WorldCover](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200) | Global 10 m land-cover masks for biome and scatter rules | Useful global raster provider after a direct tile-download contract is selected. |
| [Geofabrik extracts](https://download.geofabrik.de/) | Bulk regional OpenStreetMap PBF, Shape, and GeoPackage data | Prefer for repeated or large jobs that exceed shared Overpass limits. |

## Not separate default providers

- [Microsoft Global ML Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints)
  is permissively licensed and valuable, but Overture already integrates global building sources;
  a second default building provider would duplicate download and attribution work.
- [OpenTopography](https://opentopography.org/developers) exposes excellent global DEM APIs, but
  free keys are rate limited and commercial software integration requires an Enterprise API key.
  Do not market it as an unrestricted free provider.
