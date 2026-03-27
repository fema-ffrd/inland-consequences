# Inland Consequences Depth-Damage Function Technical Implementation

This section outlines the technical implementation of the depth-damage function workflow for the inland consequences components of the Consequences Solution. This approach may be expanded to coastal depth-damage functions in a future enhancement.

## Depth-Damage Lookup Table Generation and Source Data Overview

Before buildings are matched to depth-damage functions, the inland consequences workflow generates a set of standardized lookup tables and normalized damage-curve tables from source spreadsheets maintained in the repository. These preprocessed tables serve as the authoritative rule base used later in the assignment process and support separate workflows for structures, contents, and inventory.

The lookup-generation process uses source Excel workbooks stored in `data/source_data/`, including `OpenHazusDDFUpdates_2025.xlsx`, `Damage_Function_Deliverable_2-5-2024.xlsx`, `FL_Damage_Function_Assignment_Task4d_New_Flood_Mapping_Schemes_Business_Rules-20240213.xls`, and `Task4d_Updated_FloodDF_Approach-20240213.xlsx`. These files define the building classification logic, the mapping between building characteristics and damage-function identifiers, and the underlying depth-damage curves used by the inland consequences workflow.

For structures, `scripts/ddf_creation.py` encodes FLSBT-based mapping rules from the source data and combines them with the manually derived `foundation_flood_table_structures.csv` file (originating from `OpenHazusDDFUpdates_2025.xlsx`) to produce a fully expanded long-format lookup table. The resulting output, `outputs/df_lookup_structures.csv`, contains one row for each unique combination of construction type, occupancy type, story range, square-footage range, foundation type, and flood peril type mapped to a `Damage_Function_ID`. The script also produces `outputs/flsbt_lookup_table.csv` as an intermediate table.

For contents, `scripts/ddf_creation_cont.py` reads the “Proposed Contents DDF” sheet directly from `OpenHazusDDFUpdates_2025.xlsx` and programmatically expands it into a long-format lookup table. This workflow no longer depends on intermediate foundation flood CSVs or FLSBT codes. Instead, it expands rows across foundation categories, flood peril types, occupancy/story combinations, and construction classes to generate `outputs/df_lookup_contents.csv`.

For inventory, `scripts/ddf_creation_inv.py` unpivots `foundation_flood_table_inv.csv` (originating from `FL_Damage_Function_Assignment_Task4d_New_Flood_Mapping_Schemes_Business_Rules-20240213.xlsx`) into `outputs/df_lookup_inventory.csv`. Inventory mappings are simpler than structure or contents mappings because they are keyed directly on occupancy type, foundation type, flood peril type, and `Damage_Function_ID`, without the need for FLSBT-based expansion.

The workflow also extracts normalized depth-damage curve tables using `scripts/df_extract_curves.py`. This script produces separate outputs for structure, contents, and inventory curves and applies quality-control logic including null correction, interpolation between valid depths, and checks for non-monotonic damage behavior. Although OpenHazus 2025 introduced some curve updates, the inland consequences implementation currently continues using the 2024 curve versions because the 2025 updates did not affect inland building types and would require additional QC before full adoption.

The lookup tables use standardized code systems for foundation type and flood peril type. Foundation categories include PILE, SHAL, SLAB, and BASE. Flood peril categories include the inland riverine classes RLS, RHS, RLL, and RHL, as well as the broader coastal classes CST, CMV, and CHW preserved in the source coding framework.

The structure workflow still carries some legacy FLSBT (Flood-Specific Building Type) logic to preserve interoperability with pre-existing inland consequences schemas. FLSBT codes encode combinations of construction material, occupancy class, story range, and in some cases square footage. However, these codes were deprecated in the 2025 OpenHazus curves and may be removed entirely in a future update once downstream dependencies are no longer required.

These generated outputs form the authoritative lookup inputs for the downstream building-matching process. The assignment workflow therefore operates against preprocessed long-format lookup tables rather than deriving matching rules directly from the source spreadsheets at runtime.

## Vectorized Depth-Damage Function (DDF) Matching

This component is responsible for assigning a single Depth-Damage Function (DDF) to each building by comparing the building’s characteristics to a pre-generated lookup table of damage-function rules. The goal is to make the assignment process fast, consistent, and transparent while supporting large building inventories.

Rather than processing buildings one at a time, the implementation uses a vectorized approach, meaning that all buildings are evaluated through table-based operations rather than per-building loops. Once the lookup tables have been generated and standardized, the downstream matching function performs a merge between normalized building attributes and the complete lookup table, then filters candidate matches using story-count and square-footage range logic. The first valid match is returned for each building.

The function takes two inputs: a buildings table and a flattened lookup table. The buildings table contains one row per structure and includes attributes that influence flood damage, such as construction type, occupancy, foundation type, number of stories, square footage, and flood peril type. The lookup table contains the rules that map combinations of those attributes to specific damage-function identifiers, along with valid ranges for stories and square footage.

### Table 1. Building Table Required Fields

| Column_Name           | Description                       | Notes                                   |
| --------------------- | --------------------------------- | --------------------------------------- |
| general_building_type | Construction / material class     | Examples: W (wood)                      |
| occupancy_type        | Occupancy type                    | Examples: RES1                          |
| number_stories        | Number of stories                 | Used for story range matching           |
| area                  | Building square footage           |                                         |
| foundation_type       | Foundation type                   | Examples: SLAB, BASEMENT, SHALLOW, PILE |
| Flood_Peril_Type      | Flood hazard peril classification | Example: RLS, RHS, RLL, RHL             |

Before matching begins, the building attributes are normalized. Text fields are converted to lowercase and trimmed to avoid mismatches caused by formatting differences, and numeric fields such as story count and square footage are converted to numbers. This normalization step ensures that equivalent values are treated consistently during matching.

### Table 2. Depth-Damage Function Lookup Table Fields

| Column_Name        | Description                                        | Notes                                                                                 |
| ------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Construction_Type  | Construction type or general building type         | Must match building construction type                                                 |
| Occupancy_Type     | Occupancy type                                     | Must match building occupancy                                                         |
| Foundation_Type    | Foundation type                                    | Must match building foundation                                                        |
| Flood_Peril_Type   | Flood peril classification                         | Must match building flood peril                                                       |
| Story_Min          | Minimum supported story count                      | Inclusive                                                                             |
| Story_Max          | Maximum supported story count                      | Inclusive                                                                             |
| SQFT_Min           | Minimum supported square footage                   | Blank or null means no lower bound                                                    |
| SQFT_Max           | Maximum supported square footage                   | Blank or null means no upper bound                                                    |
| Damage_Function_ID | Depth-damage function identifier                   | Used to retrieve the DDF curve                                                        |
| FLSBT_Range        | Legacy FLSBT classification label, when applicable | Present for interoperability in structure lookup outputs generated by ddf_creation.py |

The matching process evaluates whether a building record satisfies the attribute conditions represented by the lookup table. Applicable rules include occupancy type, foundation type, number of stories, construction type, flood peril type, and square-footage bounds where those bounds are defined. These criteria are applied after the merge so that only valid lookup candidates remain. The process is designed to work against a complete long-format lookup table produced during the preprocessing stage.

### Matching Rules

- Occupancy Type Matching: When both the building and lookup row specify occupancy types, they must match exactly (for example, RES1, COM1, AGR1) for the row to remain a valid candidate.
- Foundation Type Matching: When both the building and lookup row specify foundation types, the building’s foundation code must map to the lookup foundation category. The lookup-generation framework uses standardized foundation categories such as PILE, SHAL, SLAB, and BASE, while the matching workflow may use implementation-specific equivalents such as PILE, SHALLOW, SLAB, and BASEMENT.
- Number of Stories Matching: When a lookup row contains story bounds, the building’s story count must fall within the supported range. Buildings outside all available supported ranges can be flagged through match status outputs that distinguish out-of-range conditions from direct no-match conditions. The downstream matching utility documents statuses including Matched, No_Match, Story_Out_Of_Range, and SQFT_Out_Of_Range.
- Construction Type Matching: When both the building and lookup row specify construction type, the values must match exactly.
- Square-Footage Matching: When a lookup row contains SQFT_Min and/or SQFT_Max, the building’s square footage must fall within the supported range. If square-footage thresholds are not applicable for a given lookup row, those bounds remain null and are not enforced. The structure lookup outputs generated by ddf_creation.py include square-footage range fields in the final long-format table.

The selected lookup row provides the building’s assigned Damage_Function_ID, which corresponds to a secondary depth-damage curve table. The matching function appends fields such as FLSBT_Range, Damage_Function_ID, Story_Min, Story_Max, and Match_Status to the original buildings table. Match_Status indicates whether the building was successfully matched or whether it fell outside supported story-count or square-footage ranges. The structure workflow still carries some legacy FLSBT (Flood-Specific Building Type) logic to preserve interoperability with pre-existing inland consequences schemas. FLSBT codes encode combinations of construction material, occupancy, story range, and in some cases square footage. However, these codes were deprecated in the 2025 OpenHazus curves and may be removed entirely in a future update once downstream dependencies are eliminated.

Buildings that could not be matched retain null values for damage-function fields, together with a status that explains why no assignment was made. In cases where no direct match is found, a secondary analysis (\_gather_missing_functions) is used to identify the nearest supported story-count category for the structure and assign the corresponding damage function. The record retains its no-match flag so it can still be reviewed through downstream validation logic as a potential error condition. For example, if a structure has 10 stories but the applicable attribute combination is only defined through a maximum of 4 stories, this analysis assigns the 4-story Damage_Function_ID so that every structure in the dataset receives a damage function assignment.

## Wildcard DDF Matching for Rudimentary Building Uncertainty

This section describes an exploratory matching workflow for representing rudimentary building uncertainty when assigning depth-damage functions (DDFs). Unlike the deterministic matching process described above, this approach allows a single building to retain multiple plausible DDF scenarios when some building attributes are unknown or only partially specified. The objective is to preserve uncertainty in the damage-function assignment stage so that it can be carried forward into downstream consequence calculations. This component may serve as a placeholder for more complex building uncertainty analysis developed through future research.

In this workflow, occupancy remains the primary deterministic filter, while other building attributes are treated more flexibly. The current implementation uses the building attributes occupancy, foundation, stories, and material, along with geometry and value fields (geom, val_mean, val_std) that support later consequence calculations. Hazard inputs are provided separately as return-period arrays with associated flood-depth means and standard deviations.

The lookup data are sourced from the pre-generated structure lookup table (df_lookup_structures.csv). For compatibility with the SQL logic used in the prototype, selected columns are renamed so that lookup attributes align with the building table field names. In the current implementation, construction_type is mapped to material, occupancy_type to occupancy, foundation_type to foundation, and damage_function_id to curve_id. Story matching is simplified by using story_min as the representative story value for each lookup row. The prototype also assigns placeholder first-floor-height uncertainty parameters (ffh_mu and ffh_sig) to each candidate curve.

### Wildcard Matching Concept

The distinguishing feature of this method is its use of wildcard matching for incomplete building attributes. In the prototype logic, a null building attribute does not cause a record to fail matching. Instead, null values are interpreted as “unknown,” allowing that attribute to match any corresponding lookup value. Similarly, when both the building attribute and the lookup attribute are present, they must agree exactly for the candidate curve to remain valid.

The current SQL logic applies the following rules:

- Occupancy Matching: Occupancy is required and is used as the initial filter between buildings and candidate curves. Only lookup rows with the same occupancy as the building are considered.
- Foundation Matching: If both the building and lookup row specify foundation values, they must match exactly. If either side is null, the comparison is treated as a wildcard and does not eliminate the candidate.
- Story Matching: If both the building and lookup row specify a story value, the values must match exactly in the prototype implementation. If either side is null, the candidate is retained.
- Material Matching: If both the building and lookup row specify material values, they must match exactly. If either side is null, the comparison acts as a wildcard.

Under this approach, missing or uncertain building attributes broaden the set of eligible DDFs rather than forcing an immediate no-match result. This makes the method useful for early-stage analyses, sparse inventories, or workflows in which some building characteristics are intentionally modeled as uncertain.

## Candidate Scenario Generation

The prototype constructs candidate DDF scenarios by first pairing each building with the distinct set of lookup curves that share the same occupancy. It then evaluates the wildcard matching rules described above and retains only those pairings marked as valid. The result is a set of possible curve_id values for each building rather than a single deterministic assignment.

When multiple candidate curves remain for a building, the implementation assigns a scenario weight to each one. The current weighting scheme is frequency-based: for each building, the number of times a given curve_id appears among the valid matches is divided by the total number of valid matches for that building. This produces a set of weights that sum to 1.0 across all retained scenarios for a given building.

The output of this step is a per-building list of scenario records. Each scenario contains:

- curve_id — the candidate damage-function identifier
- weight — the normalized scenario weight for that candidate
- ffh_mu — the mean first-floor-height adjustment used in subsequent depth calculations
- ffh_sig — the standard deviation associated with first-floor-height uncertainty

## Computation Grid Expansion

After candidate scenarios are generated, the workflow expands the results into a computation grid so that each building is evaluated across all combinations of hazard return period and DDF scenario. The prototype unpacks hazard inputs into one row per building and return period, including flood-depth mean and flood-depth standard deviation. It also unpacks the list of building scenarios into one row per building and candidate curve. These two expanded datasets are then joined to produce a flat table with one row per (building, return period, candidate curve) combination.

The computation grid carries forward:

- building identifiers and geometry (point_id, geom)
- building value parameters (val_mean, val_std)
- hazard descriptors (return_period, flood_depth_mean, flood_depth_std)
- candidate-curve descriptors (curve_id, weight, ffh_mu, ffh_sig)

This table structure is intended to support downstream probabilistic consequence calculations without requiring additional iterative logic.

## Structure Depth Calculation with Uncertainty

The prototype then derives structure depth statistics by combining flood-depth uncertainty with first-floor-height uncertainty. For each row in the computation grid, the structure-depth mean is computed as:

$$
\text{struct\_depth\_mean} = \text{flood\_depth\_mean} - \text{ffh\_mu}
$$

The associated uncertainty is calculated using Gaussian error propagation:

$$
\text{struct\_depth\_std}= \sqrt{flood\_depth\_std^2 + ffh\_sig^2}
$$

To support later damage-curve lookup or bounded sampling, the prototype also computes lower and upper structure-depth bounds using a three-standard-deviation interval. The lower bound is truncated at 0, and the upper bound is capped at 19 in the current implementation.

## Interpretation and Intended Use

This wildcard approach should be understood as a rudimentary uncertainty framework rather than a finalized production matching standard. The prototype demonstrates how incomplete building information can be propagated into multiple weighted DDF assignments and then carried into later consequence calculations. It is especially useful where building inventories do not contain a complete set of deterministic classification fields.
