"""Smoke test for the inland_consequences package installation."""


def verify() -> None:
    """Verify the inland_consequences package and its dependencies are correctly installed."""
    import importlib
    from importlib.resources import files

    errors = []

    checks = [
        ("inland_consequences", "InlandFloodAnalysis"),
        ("inland_consequences", "InlandFloodVulnerability"),
        ("inland_consequences", "RasterCollection"),
        ("inland_consequences", "FloodResultsAggregator"),
        ("inland_consequences", "NsiBuildings"),
        ("inland_consequences", "MillimanBuildings"),
        ("inland_consequences.coastal.pfracoastal", "Inputs"),
        ("inland_consequences.coastal.pfracoastal", "PFRACoastal"),
        ("sphere.core.schemas.buildings", "Buildings"),
        ("sphere.flood.default_vulnerability", "DefaultFloodVulnerability"),
        ("sphere.flood.single_value_reader", "SingleValueRaster"),
    ]

    schema_files = [
        "data/schemas/buildings_schema.json",
        "data/schemas/nsi_schema.json",
        "data/schemas/milliman_schema.json",
    ]

    print("Verifying inland_consequences installation...")
    for module, attr in checks:
        try:
            mod = importlib.import_module(module)
            getattr(mod, attr)
            print(f"  [OK] {module}.{attr}")
        except (ImportError, AttributeError) as e:
            errors.append(f"  [FAIL] {module}.{attr}: {e}")
            print(errors[-1])

    print("Verifying bundled schema files...")
    for schema_path in schema_files:
        try:
            files("inland_consequences").joinpath(schema_path).read_bytes()
            print(f"  [OK] inland_consequences/{schema_path}")
        except Exception as e:
            errors.append(f"  [FAIL] inland_consequences/{schema_path}: {e}")
            print(errors[-1])

    if errors:
        print(f"\n{len(errors)} check(s) failed.")
        raise SystemExit(1)
    else:
        print("\nAll checks passed. Installation is healthy.")
