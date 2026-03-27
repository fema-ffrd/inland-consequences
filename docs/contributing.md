# Contributing

Thank you for your interest in contributing to the Consequences Solution! This guide covers everything you need to get started — from setting up your environment to building and releasing the package.

______________________________________________________________________

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Clone the Repository

```bash
git clone https://github.com/fema-ffrd/inland-consequences.git
cd inland-consequences
```

### Install Dependencies

```bash
uv sync --dev
```

This installs all project and development dependencies (including `pytest`, `build`, etc.) into an isolated virtual environment managed by `uv`.

______________________________________________________________________

## Development Workflow

### Branching

Follow this branching convention:

| Branch type | Pattern                 | Example                          |
| ----------- | ----------------------- | -------------------------------- |
| Feature     | `feature/<description>` | `feature/add-coastal-validation` |
| Bug fix     | `fix/<description>`     | `fix/depth-raster-parsing`       |
| Release     | `release/<version>`     | `release/0.2.0`                  |

Always branch from `main`:

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### Running Tests

```bash
uv run pytest
```

To run only a specific test file:

```bash
uv run pytest tests/test_smoke.py -v
```

To run tests excluding manual tests:

```bash
uv run pytest -m "not manual"
```

### Code Style

Markdown files are formatted with [`mdformat`](https://mdformat.readthedocs.io/) and checked in CI on every PR and push to `main`. Run it locally before pushing to avoid CI failures:

```bash
uv run mdformat $(find docs -name '*.md' ! -name 'building_inventories.md' ! -name 'index.md' ! -name 'gh_installation.md') *.md
```

To only check without modifying:

```bash
uv run mdformat --check $(find docs -name '*.md' ! -name 'building_inventories.md' ! -name 'index.md' ! -name 'gh_installation.md') *.md
```

______________________________________________________________________

## Building the Package

The package is built as a Python wheel (`.whl`) using [Hatchling](https://hatch.pypa.io/latest/) via the [build](https://build.pypa.io/en/stable/) frontend.

### Build the Wheel

From the **repository root**, run:

```bash
uv build --wheel
```

The output will be in `dist/`:

```
dist/
  inland_consequences-0.1.0-py2.py3-none-any.whl
```

### Verify the Wheel Contents

```bash
unzip -l dist/inland_consequences-0.1.0-py2.py3-none-any.whl
```

Confirm that `inland_consequences/`, `sphere/core/`, `sphere/data/`, and `sphere/flood/` are all present.

### Test the Wheel in a Clean Environment

```bash
uv venv /tmp/test_whl_env
source /tmp/test_whl_env/bin/activate
uv pip install dist/inland_consequences-0.1.0-py2.py3-none-any.whl
inland-consequences-check
deactivate
rm -rf /tmp/test_whl_env
```

The `inland-consequences-check` CLI entry point runs a smoke test that validates all public modules and classes are importable.

______________________________________________________________________

## Releasing

Releases are **fully automated** via the [`.github/workflows/release.yml`](https://github.com/fema-ffrd/inland-consequences/blob/main/.github/workflows/release.yml) GitHub Action. Pushing a version tag triggers the workflow, which builds the wheel and publishes a GitHub Release with the `.whl` attached automatically.

### Pre-release (rc / test)

Use a tag containing `rc`, `alpha`, `beta`, `test`, or `dev` to publish a **pre-release** — useful for testing install docs on a clean machine before cutting a final release.

```bash
git tag v0.1.0-rc.1
git push origin v0.1.0-rc.1
```

GitHub will mark the release as **Pre-release** automatically. To clean it up afterward:

```bash
# Delete the remote tag
git push origin --delete v0.1.0-rc.1
# Delete the local tag
git tag -d v0.1.0-rc.1
```

Also delete the corresponding release on the [Releases page](https://github.com/fema-ffrd/inland-consequences/releases).

______________________________________________________________________

### Full Release

#### 1. Prepare the Release Branch

```bash
git checkout -b release/0.x.0
```

Update the version in `pyproject.toml`, commit all changes, and open a PR.

#### 2. Tag and Push

Once the release branch is ready:

```bash
git tag v0.x.0
git push origin release/0.x.0
git push origin v0.x.0
```

The workflow triggers automatically, builds the wheel, and publishes a GitHub Release with auto-generated release notes.

#### 3. Merge to Main

```bash
git checkout main
git pull origin main
git merge release/0.x.0
git push origin main
```

!!! note
    The wheel binary should **not** be committed to version control. The workflow attaches it as a GitHub Release asset automatically.

______________________________________________________________________

## Submitting Changes

1. Ensure all tests pass: `uv run pytest`
1. Ensure pre-commit hooks pass: `uv run pre-commit run --all-files`
1. Push your branch and open a Pull Request against `main`.
1. Provide a clear description of the change and any relevant context.
1. A maintainer will review and merge your PR.

______________________________________________________________________

## Reporting Issues

Please open an issue on [GitHub](https://github.com/fema-ffrd/inland-consequences/issues) with:

- A clear description of the bug or feature request
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Python version and OS
