# Inland Consequences Depth-Damage Function Technical Implementation

This outlines the technical implementation of the depth-damage function for the inland consequences aspects of the Consequences Solution. This approach may be expanded to coastal depth-damage functions in a future enhancement.

## Vectorized Depth-Damage Function (DDF) Matching

This component is responsible for assigning a single Depth-Damage Function (DDF) to each building by comparing the building’s characteristics to a pre-generated lookup table of damage-function rules. The goal is to make the assignment process fast, consistent, and transparent while supporting large building inventories.

Rather than processing buildings one at a time, the implementation uses a vectorized approach, meaning that all buildings are evaluated simultaneously using table joins and grouped logic. This avoids slow per-building loops and ensures that the same rules are applied uniformly across the dataset.

The function takes two inputs: a buildings table and a flattened lookup table. The buildings table contains one row per structure and includes attributes that influence flood damage, such as construction type, occupancy, foundation type, number of stories, square footage, and flood peril type. The lookup table contains the rules that map combinations of those attributes to specific damage-function identifiers, along with valid ranges for stories and square footage.

**Table 1. Building Table Required Fields**

| Column_Name           | Description                       | Notes                                   |
| --------------------- | --------------------------------- | --------------------------------------- |
| S_GENERALBUILDINGTYPE | Construction / material class     | Examples: W (wood)                      |
| S_OCCTYPE             | Occupancy type                    | Examples: RES1                          |
| S_NUMSTORY            | Number of stories                 | Used for story range matching           |
| S_SQFT                | Building square footage           |                                         |
| Foundation_Type       | Foundation type                   | Examples: SLAB, BASEMENT, SHALLOW, PILE |
| Flood_Peril_Type      | Flood hazard peril classification | Example: RLS, RHS, RLL, RHL             |

Before matching begins, the building attributes are normalized. Text fields are converted to lowercase and trimmed to avoid mismatches caused by formatting differences, and numeric fields such as story count and square footage are converted to numbers. This normalization step ensures that equivalent values are treated consistently during matching.

**Table 2. Depth-Damage Function Lookup Table Fields**

| Column_Name        | Description                                | Notes                                 |
| ------------------ | ------------------------------------------ | ------------------------------------- |
| Construction_Type  | Construction type or general building type | Must match building construction type |
| Occupancy_Type     | Occupancy type                             | Must match building occupancy         |
| Foundation_Type    | Foundation type                            | Must match building foundation        |
| Flood_Peril_Type   | Flood peril classification                 | Must match building flood peril       |
| Story_Min          | Minimum supported story count              | Inclusive                             |
| Story_Max          | Maximum supported story count              | Inclusive                             |
| SQFT_Min           | Minimum supported square footage           | Blank or null means no lower bound    |
| SQFT_Max           | Maximum supported square footage           | Blank or null means no upper bound    |
| Damage_Function_ID | Depth-damage function identifier           | Used to retrieve the DDF curve        |

The matching process identifies applicable damage functions for each building using a single SQL CASE statement that evaluates multiple attribute conditions. The process begins with a cross join between the buildings table and all available damage function curves, generating every possible building-to-curve pairing. The matching logic then evaluates a series of attribute-based conditions to determine which pairings are valid.

**Occupancy Type Matching:** When both the building and the curve specify occupancy types (i.e., neither value is NULL), they must match exactly (for example, RES1, COM1, AGR1) for the pairing to be considered valid. If either value is NULL, this constraint is not applied. This condition can be disabled through wildcard configuration.

**Foundation Type Matching:** When both the building and curve specify foundation types (neither is NULL), the building's foundation code must map to the curve's foundation category. This is using the pile, basement, slab, shallow categories consistent with inland methodology described in the building inventory technical implementation documentation. When either value is NULL, this constraint is not applied. This check can be disabled via wildcard configuration.

**Number of Stories Matching:** When all three values are present for building stories, curve's story_min, and story_max, the building's story count must fall within the curve's specified range. When any of these values is NULL, this constraint is not applied. Buildings with story counts that exceed all available maximum values will eventually be assigned the damage function with the largest allowed maximum story count. This check can be disabled via wildcard configuration.

**Construction Type Matching:** When both the building’s construction type and the curve's construction type are present (neither is NULL), they must match exactly. When either value is NULL, this constraint is not applied. This check can be disabled via wildcard configuration.

For each building-curve pairing, any failed condition marks the pairing as invalid (is_match = 0). A pairing that passes all applicable conditions is marked as valid (is_match = 1). Only pairings where is_match = 1 are retained for further processing.

When multiple damage function curves match a building, the system calculates probability weights by counting how many times each unique damage function appears and dividing by the total number of matches for that building. This ensures weights sum to 1.0 for each building and produces a weighted set of applicable damage functions.

For candidates, that exceed the range for the number of stories or square-footage, they are assigned the highest allowed values for their attribute combination.

The selected lookup row provides the building’s assigned Damage Function ID, which corresponds to a secondary lookup table containing the percentage damage at each stage depth. The function returns the original buildings table with additional columns appended. These columns include the selected damage-function identifier, the matched story range, and the match status. Buildings that could not be matched retain null values for the damage-function fields, along with a status that explains why no assignment was made.
