# Install from GitHub Release

The **Consequences Solution** is distributed as a Python wheel (`.whl`) attached to each [GitHub Release](https://github.com/fema-ffrd/inland-consequences/releases). No PyPI account or index configuration is required.

---

## Prerequisites

- Python 3.10 or higher
- `pip` (comes bundled with Python)

---

## Installation Steps

### 1. Download the Wheel

Navigate to the [Releases page](https://github.com/fema-ffrd/inland-consequences/releases) and download the `.whl` file from the latest release assets, for example:

```
inland_consequences-0.1.0-py2.py3-none-any.whl
```

### 2. Install with pip

```bash
pip install inland_consequences-0.1.0-py2.py3-none-any.whl
```

### 3. Verify the Installation

Run the built-in smoke check to confirm all modules loaded correctly:

```bash
inland-consequences-check
```

A successful installation produces the following output:

```
Verifying inland_consequences installation...
  [OK] inland_consequences.InlandFloodAnalysis
  [OK] inland_consequences.InlandFloodVulnerability
  [OK] inland_consequences.RasterCollection
  [OK] inland_consequences.FloodResultsAggregator
  [OK] inland_consequences.NsiBuildings
  [OK] inland_consequences.MillimanBuildings
  [OK] inland_consequences.coastal.pfracoastal.Inputs
  [OK] inland_consequences.coastal.pfracoastal.PFRACoastal
  [OK] sphere.core.schemas.buildings.Buildings
  [OK] sphere.flood.default_vulnerability.DefaultFloodVulnerability
  [OK] sphere.flood.single_value_reader.SingleValueRaster

All checks passed. Installation is healthy.
```

If any line reports `[FAIL]`, re-install the wheel or open an issue on the [GitHub repository](https://github.com/fema-ffrd/inland-consequences/issues).

---

## Installing in a Virtual Environment

It is recommended to install into an isolated environment. Select your preferred tool and run the commands in your terminal:

=== "venv"

    ```bash
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

=== "uv"

    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

=== "conda"

    ```bash
    conda create -n consequences python=3.12
    conda activate consequences
    pip install inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

---

## Installing via an Environment File

To pin the package in a reproducible environment, reference the wheel URL directly from the GitHub Release. Select your environment manager:

=== "requirements.txt"

    Add the direct wheel URL to your `requirements.txt`:

    ```txt title="requirements.txt"
    https://github.com/fema-ffrd/inland-consequences/releases/download/v0.1.0/inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

    Then install:

    ```bash
    pip install -r requirements.txt
    ```

=== "environment.yml"

    Reference the wheel URL under the `pip:` section of your Conda `environment.yml`:

    ```yaml title="environment.yml"
    name: consequences
    channels:
      - defaults
    dependencies:
      - python=3.12
      - pip
      - pip:
        - https://github.com/fema-ffrd/inland-consequences/releases/download/v0.1.0/inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

    Then create the environment:

    ```bash
    conda env create -f environment.yml
    conda activate consequences
    ```

=== "Dockerfile"

    Copy the wheel into the image and install it at build time:

    ```dockerfile title="Dockerfile"
    FROM python:3.12-slim

    # libexpat1 is stripped from slim images but required at runtime
    RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /app

    # Copy the wheel from the build context (download it first)
    COPY inland_consequences-0.1.0-py2.py3-none-any.whl .

    RUN pip install --no-cache-dir inland_consequences-0.1.0-py2.py3-none-any.whl

    # Verify the install
    RUN inland-consequences-check
    ```

    Alternatively, install directly from the release URL without a local copy:

    ```dockerfile title="Dockerfile (remote)"
    FROM python:3.12-slim

    # libexpat1 is stripped from slim images but required at runtime
    RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
        && rm -rf /var/lib/apt/lists/*

    RUN pip install --no-cache-dir \
        https://github.com/fema-ffrd/inland-consequences/releases/download/v0.1.0/inland_consequences-0.1.0-py2.py3-none-any.whl
    ```

---

## Upgrading

When a new release is available, download the new `.whl` file and re-install with the `--upgrade` flag:

```bash
pip install --upgrade inland_consequences-0.2.0-py2.py3-none-any.whl
```
