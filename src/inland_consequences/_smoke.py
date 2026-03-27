"""Smoke test for the inland_consequences package installation."""


def verify() -> None:
    """Verify the inland_consequences package and its dependencies are correctly installed."""
    import importlib

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

    print("Verifying inland_consequences installation...")
    for module, attr in checks:
        try:
            mod = importlib.import_module(module)
            getattr(mod, attr)
            print(f"  [OK] {module}.{attr}")
        except (ImportError, AttributeError) as e:
            errors.append(f"  [FAIL] {module}.{attr}: {e}")
            print(errors[-1])

    if errors:
        print(f"\n{len(errors)} check(s) failed.")
        raise SystemExit(1)
    else:
        print("\nAll checks passed. Installation is healthy.")
