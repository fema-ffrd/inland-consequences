# Inland Consequences

This project aims to create a unified methodology for consequence modeling that seamlessly integrates both coastal and inland approaches, providing adaptable and efficient solutions for a wide range of scenarios. For more details on this project, please view our [Consequences Solution documentation](https://fema-ffrd.github.io/inland-consequences/).

## Prerequisites

Install `uv` if you haven't already:

**Linux/macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows PowerShell:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For other installation methods, see the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/).

## Environment and Docs Setup

1. Create a Python virtual environment and install dependencies

```powershell
uv sync --all-packages
```

2. Run tests

```powershell
uv run pytest -q
```

3. Run the local `mkdocs` server.

```
uv run mkdocs serve
```

### Optional Setup - Markdown Formatting Pre-Commit Hook

To set up a pre-commit hook for [mdformat](https://mdformat.readthedocs.io/en/stable/index.html) to automatically format Markdown files within the repository:

```
(venv-inland) $ pre-commit install
```

### Optional Test inspections

You can run the pytest tests from the command line to direct where to put the temporary
files that it generates when the test are run.

```powershell
uv run pytest -m manual tests/test_inland_flood_analysis.py  --basetemp=outputs
```

After that is run, you can inspect the generated files in the outputs folder for each test
and open the DuckDB file using the DuckDB CLI.

```powershell
uv run duckdb -ui .\outputs\test_manual_calculate_lossescurrent\test_duwamish.duckdb
```