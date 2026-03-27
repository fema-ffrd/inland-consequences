"""Tests to verify _smoke.py checks stay in sync with actual modules and classes."""

import importlib
import pytest
from inland_consequences._smoke import verify


def _get_checks():
    """Extract the checks list from the verify function's source."""
    import inland_consequences._smoke as smoke_module
    import inspect
    import ast

    source = inspect.getsource(smoke_module)
    tree = ast.parse(source)

    checks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "checks":
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                            module = elt.elts[0].value
                            attr = elt.elts[1].value
                            checks.append((module, attr))
    return checks


@pytest.mark.parametrize("module,attr", _get_checks())
def test_smoke_check_is_valid(module, attr):
    """Each (module, attr) entry in _smoke.py checks must be importable and accessible."""
    mod = importlib.import_module(module)
    assert hasattr(mod, attr), (
        f"{module}.{attr} not found — update _smoke.py to match the current codebase."
    )


def test_verify_runs_without_error():
    """The verify() function itself must complete without raising SystemExit."""
    verify()
