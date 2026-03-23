# Data: Damage Function Lookup Table Generation

This folder contains the source data and derived lookup tables used to generate damage function (DDF) assignments for the inland flood consequence model. Scripts in `scripts/` process these files to produce long-format lookup CSVs that map building characteristics (construction type, occupancy, foundation, stories, square footage) and flood hazard type to a specific damage function ID.

---

## Folder Contents

### `source_data/` — Source Excel Files

| File | Purpose |
|---|---|
| `source_data/OpenHazusDDFUpdates_2025.xlsx` | Primary source for structures and contents damage function assignments |
| `source_data/Damage_Function_Deliverable_2-5-2024.xlsx` | Source for damage curves and inventory damage function assignments |
| `source_data/Task4d_Updated_FloodDF_Approach-20240213.xlsx` | Reference for decoding FLSBT codes to building characteristics (construction, occupancy, stories, SQFT) |

### Foundation Flood Tables — Derived CSVs

These CSVs are **manually derived** from the Excel source files (see Step 0 below). They use a pivoted layout where:
- **Rows** are FLSBT codes (for structures/contents) or occupancy types (for inventory)
- **Columns** form a two-level header: Foundation Type (row 1) × Flood Peril Type (row 2), yielding 28 columns (4 foundations × 7 perils)
- **Cells** contain the integer DDF ID assigned to that combination

| File | Asset Type | Source |
|---|---|---|
| `foundation_flood_table_structures.csv` | Structures | `source_data/OpenHazusDDFUpdates_2025.xlsx` |
| `foundation_flood_table_cont1.csv` | Contents (FLSBT-based) | `source_data/OpenHazusDDFUpdates_2025.xlsx` |
| `foundation_flood_table_cont2.csv` | Contents (story-specific occupancies) | `source_data/OpenHazusDDFUpdates_2025.xlsx` |
| `foundation_flood_table_inv.csv` | Inventory | `source_data/Damage_Function_Deliverable_2-5-2024.xlsx` |

These CSVs are checked in and do not need to be regenerated unless the source Excel files change.

---

## Code Keys

### Flood Peril Types

The foundation flood tables use a two-row MultiIndex header: the first row is **Foundation Type**, the second is **Flood Peril Type**. There are 7 flood peril categories:

| Code | Full Name | Description |
|---|---|---|
| `RLS` | Riverine Low Velocity, Short Duration | Typical Riverine AE zone, non-floodway |
| `RHS` | Riverine High Velocity, Short Duration | Typical Riverine VE zone / floodway |
| `RLL` | Riverine Low Velocity, Long Duration | Riverine AE zone with prolonged inundation |
| `RHL` | Riverine High Velocity, Long Duration | Riverine VE zone with prolonged inundation |
| `CST` | Coastal Stillwater | Coastal AE flood hazard |
| `CMV` | Coastal Moderate Wave | Coastal AE based on Limit of Moderate Wave Action (LiMWA) |
| `CHW` | Coastal High Wave | Coastal VE zone |

### Foundation Types

| Code | Description |
|---|---|
| `PILE` | Pile / pier foundation |
| `SHAL` | Shallow foundation (slab-on-grade, crawlspace) |
| `SLAB` | Slab-on-grade |
| `BASE` | Basement |

### FLSBT Codes

FLSBT (Flood-Specific Building Type) codes encode a combination of construction material, occupancy class, story range, and sometimes square footage. For example, `WSF001` represents a wood single-family structure. The full mapping of FLSBT codes to building characteristics is documented in `source_data/Task4d_Updated_FloodDF_Approach-20240213.xlsx`. The script `scripts/flsbt_generate.py` produces the programmatic version of this mapping as a CSV.

---

## Generating the Lookup Tables

Run all scripts from the **repository root**.

### Step 0 — Manual Table Extraction (one-time setup)

The `foundation_flood_table_*.csv` files are manually extracted from the source Excel files. Re-extract them only if the source Excel files change.

### Track A — Structures

`scripts/ddf_creation.py` encodes the FLSBT mapping rules from `source_data/OpenHazusDDFUpdates_2025.xlsx` into an intermediate lookup table, then combines it with the unpivoted `foundation_flood_table_structures.csv` to produce a fully expanded long-format lookup. Each row maps a unique combination of building attributes + foundation + flood peril to a DDF ID. The intermediate FLSBT table is also saved as a side-effect.

```bash
uv run python scripts/ddf_creation.py
```

**Input:** `data/foundation_flood_table_structures.csv`

**Outputs:**
- `outputs/flsbt_lookup_table.csv` — intermediate FLSBT mapping rules
- `outputs/df_lookup_structures.csv` — final structures lookup table

Columns (final table): `Construction_Type`, `Occupancy_Type`, `Story_Min`, `Story_Max`, `SQFT_Min`, `SQFT_Max`, `Foundation_Type`, `Flood_Peril_Type`, `FLSBT_Range`, `Damage_Function_ID`

> **Note:** `scripts/flsbt_generate.py` is a deprecated standalone script that contains the same FLSBT generation logic. It is superseded by `ddf_creation.py` and does not need to be run separately.

### Track A — Contents

`scripts/ddf_creation_cont.py` follows the same FLSBT-based approach as the structures script, but with two sources:

1. **FLSBT path** — Most building types go through the standard FLSBT lookup using `foundation_flood_table_cont1.csv`.
2. **Occupancy path** — Certain occupancies (e.g., COM4) have story-specific damage functions tracked separately in `foundation_flood_table_cont2.csv`, handled by `unpivot_occupancy_flood_table_cont()`. These rows are merged back into the final table.

```bash
uv run python scripts/ddf_creation_cont.py
```

**Inputs:**
- `outputs/flsbt_lookup_table_contents.csv` (generated internally during the run)
- `data/foundation_flood_table_cont1.csv`
- `data/foundation_flood_table_cont2.csv`

**Output:** `outputs/df_lookup_contents.csv`

Columns match `df_lookup_structures.csv`.

### Track B — Inventory

Inventory damage functions are simpler: no FLSBT codes are needed. The lookup is keyed directly on **occupancy type** (e.g., COM1, IND3). `scripts/ddf_creation_inv.py` unpivots `foundation_flood_table_inv.csv` into long format.

The inventory tables are sourced from `source_data/Damage_Function_Deliverable_2-5-2024.xlsx`.

```bash
uv run python scripts/ddf_creation_inv.py
```

**Input:** `data/foundation_flood_table_inv.csv`

**Output:** `outputs/df_lookup_inventory.csv`

Columns: `Occupancy_Type`, `Foundation_Type`, `Flood_Peril_Type`, `Damage_Function_ID`

### Damage Curves

`scripts/df_extract_curves.py` extracts the actual depth-damage curves from `source_data/Damage_Function_Deliverable_2-5-2024.xlsx` into normalized CSVs. It handles three asset types (structure, contents, inventory), corrects null values (zero-filling before first valid depth, forward-filling at max after last valid depth, linear interpolation between valid depths), and flags any curves where damage decreases with depth.

```bash
uv run python scripts/df_extract_curves.py
```

**Input:** `data/source_data/Damage_Function_Deliverable_2-5-2024.xlsx`

**Outputs:**
- `outputs/damage_curves_structure.csv`
- `outputs/damage_curves_contents.csv`
- `outputs/damage_curves_inventory.csv`

Columns: `DDF_ID`, `Originator_Source`, then one column per depth increment from `-12 ft` to `+24 ft` (half-foot increments, e.g., `ft12m`, `ft1_5m`, `ft00`, `ft0_5`, `ft01`, ... `ft24`).

---

## Downstream: Matching Buildings to Damage Functions

`scripts/match_ddf.py` provides a vectorized function for assigning a `Damage_Function_ID` to each building in a dataset. It performs a left-merge on normalized building attributes against the complete lookup table, filtering by story and SQFT ranges, and returns the first matching row per building.

```python
from scripts.match_ddf import lookup_damage_function

result = lookup_damage_function(buildings_df, complete_lookup_table)
# Adds columns: FLSBT_Range, Damage_Function_ID, Story_Min, Story_Max, Match_Status
# Match_Status: "Matched" | "No_Match" | "Story_Out_Of_Range" | "SQFT_Out_Of_Range"
```

---

## Summary of Outputs

| Output File | Script | Asset Type |
|---|---|---|
| `outputs/flsbt_lookup_table.csv` | `scripts/ddf_creation.py` | Structures (intermediate) |
| `outputs/flsbt_lookup_table_contents.csv` | `scripts/ddf_creation_cont.py` | Contents (intermediate) |
| `outputs/df_lookup_structures.csv` | `scripts/ddf_creation.py` | Structures |
| `outputs/df_lookup_contents.csv` | `scripts/ddf_creation_cont.py` | Contents |
| `outputs/df_lookup_inventory.csv` | `scripts/ddf_creation_inv.py` | Inventory |
| `outputs/damage_curves_structure.csv` | `scripts/df_extract_curves.py` | Structures |
| `outputs/damage_curves_contents.csv` | `scripts/df_extract_curves.py` | Contents |
| `outputs/damage_curves_inventory.csv` | `scripts/df_extract_curves.py` | Inventory |
