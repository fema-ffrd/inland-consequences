# API Reference

This section provides detailed API documentation for the Inland Consequences packages.

## Packages

### inland_consequences

The main package containing flood analysis orchestration, vulnerability calculations, and building data handling.

- [inland_flood_analysis](inland_consequences/inland_flood_analysis.md) - Vectorized inland flood analysis orchestrator
- [inland_vulnerability](inland_consequences/inland_vulnerability.md) - Inland vulnerability function implementation
- [raster_collection](inland_consequences/raster_collection.md) - Raster input management for multi-return-period analysis
- [results_aggregation](inland_consequences/results_aggregation.md) - Flood results aggregation utilities
- [nsi_buildings](inland_consequences/nsi_buildings.md) - NSI (National Structure Inventory) building data handling
- [milliman_buildings](inland_consequences/milliman_buildings.md) - Milliman building data handling

### Coastal Submodule

- [pfracoastal](inland_consequences/coastal/pfracoastal.md) - PFRA coastal flood analysis

### sphere.core.schemas

Core schemas and abstract interfaces used across the consequence modeling framework.

- [buildings](sphere_core/buildings.md) - Base Buildings class with field mapping
- [field_mapping](sphere_core/field_mapping.md) - Field mapping utilities for flexible column naming
- [abstract_raster_reader](sphere_core/abstract_raster_reader.md) - Abstract interface for raster data readers
- [abstract_vulnerability_function](sphere_core/abstract_vulnerability_function.md) - Abstract vulnerability function interface
- [nsi_buildings](sphere_core/nsi_buildings.md) - NSI-specific buildings schema
