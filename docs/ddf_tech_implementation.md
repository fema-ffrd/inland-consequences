# Inland Consequences Depth-Damage Function Technical Implementation

This outlines the technical implementation of the depth-damage function for the inland consequences aspects of the Consequences Solution. This approach may be expanded to coastal depth-damage functions in a future enhancement.

## Vectorized Depth-Damage Function (DDF) Matching

This component is responsible for assigning a single Depth-Damage Function (DDF) to each building by comparing the building’s characteristics to a pre-generated lookup table of damage-function rules. The goal is to make the assignment process fast, consistent, and transparent while supporting large building inventories.

Rather than processing buildings one at a time, the implementation uses a vectorized approach, meaning that all buildings are evaluated simultaneously using table joins and grouped logic. This avoids slow per-building loops and ensures that the same rules are applied uniformly across the dataset.

The function takes two inputs: a buildings table and a flattened lookup table. The buildings table contains one row per structure and includes attributes that influence flood damage, such as construction type, occupancy, foundation type, number of stories, square footage, and flood peril type. The lookup table contains the rules that map combinations of those attributes to specific damage-function identifiers, along with valid ranges for stories and square footage.

**Table 1. Building Table Required Fields**

| Column_Name           | Description                   | Notes                                                       |
| --------------------- | ----------------------------- | ----------------------------------------------------------- |
| S_GENERALBUILDINGTYPE | Construction / material class | Examples: W (wood), C (concrete), S (steel)                 |
| S_OCCTYPE             | Occupancy type                | Examples: RES1, COM1                                        |
| S_NUMSTORY            | Number of stories             | Used for story range matching                               |
| S_SQFT                | Building square footage       | Optional; defaults to 0 if missing                          |
| Foundation_Type       | Foundation type               | Examples: SLAB, BASE, CRAWL                                 |
| Flood_Peril_Type      | Flood peril classification    | Used to distinguish flood types (e.g., riverine vs coastal) |

Before matching begins, the building attributes are normalized. Text fields are converted to uppercase and trimmed to avoid mismatches caused by formatting differences, and numeric fields such as story count and square footage are converted to numbers. This normalization step ensures that equivalent values are treated consistently during matching.

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
| FLSBT_Range        | Descriptive story range label              | Used for diagnostics and reporting    |
| Damage_Function_ID | Depth-damage function identifier           | Used to retrieve the DDF curve        |

The matching process begins by identifying candidate lookup rows for each building. This is done by requiring an exact match on a small set of core attributes: construction type, occupancy type, foundation type, and flood peril type. These attributes define the basic damage context for a building and act as the primary filter.

If no lookup rows match on these core attributes, the building is marked as having no applicable damage function. If one or more candidate rows exist, the process continues to more detailed checks on the number of stories.

The function evaluates whether the building’s number of stories falls within the valid range specified by each lookup row. A building must have a story count that lies between the lookup row’s minimum and maximum values to remain a valid match. If none of the candidates meet this condition, the building is flagged as being outside the supported story range.

For candidates that pass the story check, the function then evaluates square footage constraints. Some lookup rows specify minimum or maximum square-footage limits, while others do not. When no limits are provided, the range is treated as unbounded. If square-footage limits are present, the building’s size must fall within those bounds. Buildings that pass the story check but fail all square-footage checks are flagged accordingly.

**Table 3. Match Status Decriptions**

| Match_Status       | Meaning                                                                             | What it indicates                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| No_Match           | No lookup row matched the required key attributes                                   | The building’s construction, occupancy, foundation, or flood peril type is not represented in the lookup table |
| Story_Out_Of_Range | Lookup candidates existed, but none covered the building’s story count              | The building type is recognized, but its number of stories falls outside all supported story ranges            |
| SQFT_Out_Of_Range  | Lookup candidates matched the building type and story range, but not square footage | The building size falls outside the square-footage limits defined in the lookup rules                          |
| Matched            | At least one lookup row passed all matching checks                                  | A valid depth-damage function was assigned to the building                                                     |

For candidates, that exceed the range for the number of stories or square-footage, they are assigned the highest allowed values for their attribute combination.

The selected lookup row provides the building’s assigned Damage Function ID, which corresponds to a secondary lookup table containing the percentage damage at each stage depth. The function returns the original buildings table with additional columns appended. These columns include the selected damage-function identifier, the matched story range, and the match status. Buildings that could not be matched retain null values for the damage-function fields, along with a status that explains why no assignment was made.
