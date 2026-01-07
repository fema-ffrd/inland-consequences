# Inventory Methodology

The **Consequences Solution** is designed to operate out of the box with two predefined national inventories: the **National Structures Inventory (NSI)** and the **Milliman Market Basket Data**. Users may also integrate their own **custom structure inventories** by defining a corresponding **JSON schema**. For additional guidance on NSI Milliman inventories, and configuring and loading custom inventories, refer to the [**Technical Implementation Documentation**](building_inventories.md).

______________________________________________________________________

## Inventory Dataset Format

The **Consequences Solution** currently accepts input inventory datasets in **point geometry** format, representing the location of each structure to be analyzed. Supported input formats include **Comma-Separated Values (.csv)**, **Esri Shapefile (.shp)**, **File Geodatabase (.gdb)**, and **GeoPackage (.gpkg)**. Each record should include the **required attribute fields** used in the loss calculations, and all spatial data should be stored in a **projected coordinate system** appropriate for the analysis extent. Using point-based inputs ensures compatibility with the **consequence modeling workflow** and enables efficient spatial joins with hazard and inventory datasets.

______________________________________________________________________

## Inventory Attributes Used in Analysis

The following attributes are used in the **Consequences Solution** loss calculations. While providing all recommended fields from the input inventory dataset ensures more accurate loss estimates, missing attributes will automatically be populated with **default values**. However, reliance on these defaults may reduce the precision of results.

Loss calculations for **inland** and **coastal** areas require different sets of input attributes.
**Table 1** outlines the required inventory inputs for inland loss calculations, while **Table 4** details the corresponding inputs for coastal loss calculations.

**Table 1. Inventory Input Data Requirements for Inland Consequence Modeling**

| **Input Data**                       | **Required / Optional** | **Purpose**                                                                                                                                                             | **Default Process If Data Not Provided**                                                                                                                                                                                     |
| ------------------------------------ | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Geometry**                         | Required                | Locational geometry is required for spatial analysis.                                                                                                                   | None, required input. If CSV option added, alt and long fields would replace this.                                                                                                                                           |
| **Unique ID**                        | Required                | Used for identifying the structure throughout analysis.                                                                                                                 | None, required input.                                                                                                                                                                                                        |
| **Occupancy Type**                   | Optional                | Primary use is for the selection of depth damage functions in analysis. A secondary use is to provide default values if square footage/area attribution is unavailable. | Defaults to **RES1**.                                                                                                                                                                                                        |
| **Building Value**                   | Required                | Used for the calculation of structural loss.                                                                                                                            | None, required input. See *Hazus Inventory Manual* if guidance is required.                                                                                                                                                  |
| **Content Value**                    | Optional                | Used for the calculation of content loss.                                                                                                                               | If not provided, structures will be assigned a default content value based on a percentage of the building value for each Occupancy Type following the Hazus Methodology. See **Table 3** for percentages by occupancy type. |
| **Number of Stories**                | Optional                | Used for the assignment of depth damage functions in analysis.                                                                                                          | Defaults to **1 story**. Important for **RES1** when available, as DDFs differ significantly. Cannot exceed **3** for RES1.                                                                                                  |
| **Area / Square Footage**            | Optional                | Used for assigning depth damage functions and for calculations such as debris and income-related losses.                                                                | If not provided, structures will be assigned a default area based on typical square footage by Occupancy Type from the *Hazus Methodology* (see **Table 2**).                                                                |
| **General Building Type**            | Optional                | Used for assignment of depth damage function for inland analysis.                                                                                                       | Defaults to **W (Wood)**. Hazus tract-level mapping schemes by occupancy type (*hzGenBldgScheme*) can be used to enhance inventories.                                                                                        |
| **Foundation Type**                  | Optional                | Used for selecting the appropriate depth damage function.                                                                                                               | Defaults to **Slab**. Hazus mapping schemes (also used by **NSI**) are available for users to enhance inventories.                                                                                                           |
| **Foundation Height**                | Optional                | Used to determine depth of water within a structure.                                                                                                                    | Defaults: **Slab = 1 ft**, **Shallow = 3 ft**, **Pile = 8 ft**, **Basement = 2 ft**. Adjustments can be considered for pre- and post-FIRM structures.                                                                        |
| **Foundation Type from Parcel Data** | Optional                | Used, if available, to refine foundation type assignment.                                                                                                               | --                                                                                                                                                                                                                           |
| **Basement Type from Parcel Data**   | Optional                | Used, if available, to refine foundation type assignment.                                                                                                               | --                                                                                                                                                                                                                           |

**Table 2. Hazus Methodology for Default Building Square Footage by Occupancy Type**

| **Occupancy Type** | **Square Footage** |
| ------------------ | -----------------: |
| AGR1               |             30,000 |
| COM1               |            110,000 |
| COM10              |            145,000 |
| COM2               |             30,000 |
| COM3               |             10,000 |
| COM4               |             80,000 |
| COM5               |              4,100 |
| COM6               |             55,000 |
| COM7               |              7,000 |
| COM8               |              5,000 |
| COM9               |             12,000 |
| EDU1               |            130,000 |
| EDU2               |             50,000 |
| GOV1               |             11,000 |
| GOV2               |             11,000 |
| IND1               |             30,000 |
| IND2               |             30,000 |
| IND3               |             45,000 |
| IND4               |             45,000 |
| IND5               |             45,000 |
| IND6               |             30,000 |
| REL1               |             17,000 |
| RES1               |              1,800 |
| RES2               |              1,475 |
| RES3A              |              2,200 |
| RES3B              |              4,400 |
| RES3C              |              8,000 |
| RES3D              |             15,000 |
| RES3E              |             40,000 |
| RES3F              |             80,000 |
| RES4               |            135,000 |
| RES5               |             25,000 |
| RES6               |             25,000 |

**Table 3. Content Value as Percent of Building Value by Occupancy Type**

| **Occupancy Type** | **Content Value (%)** |
| ------------------ | --------------------: |
| AGR1               |                  100% |
| COM1               |                  100% |
| COM10              |                   50% |
| COM2               |                  100% |
| COM3               |                  100% |
| COM4               |                  100% |
| COM5               |                  100% |
| COM6               |                  150% |
| COM7               |                  150% |
| COM8               |                  100% |
| COM9               |                  100% |
| EDU1               |                  100% |
| EDU2               |                  150% |
| GOV1               |                  100% |
| GOV2               |                  150% |
| IND1               |                  150% |
| IND2               |                  150% |
| IND3               |                  150% |
| IND4               |                  150% |
| IND5               |                  150% |
| IND6               |                  100% |
| REL1               |                  100% |
| RES1               |                   50% |
| RES2               |                   50% |
| RES3A              |                   50% |
| RES3B              |                   50% |
| RES3C              |                   50% |
| RES3D              |                   50% |
| RES3E              |                   50% |
| RES3F              |                   50% |
| RES4               |                   50% |
| RES5               |                   50% |
| RES6               |                   50% |

**Table 4. Inventory Input Data Requirements for Coastal Consequence Modeling**

| **Input Data**                             | **Required / Optional** | **Purpose**                                                    | **Default Process**                                                                                                                                                                                   |
| ------------------------------------------ | ----------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Geometry**                               | Required                | Locational geometry is required for spatial analysis.          | None, required input.                                                                                                                                                                                 |
| **Unique ID**                              | Required                | Used for identifying the structure throughout analysis.        | None, required input.                                                                                                                                                                                 |
| **Building Value**                         | Required                | Used for the calculation of structural loss.                   | None, required input.                                                                                                                                                                                 |
| **Ground Elevation**                       | Required                | Used to determine depth of water in structure.                 | None, required input.                                                                                                                                                                                 |
| **Number of Stories**                      | Optional                | Used for the assignment of depth damage functions in analysis. | Defaults to **1 story** if data not provided.                                                                                                                                                         |
| **Foundation Type**                        | Optional                | Used for the selection of the depth damage function.           | Defaults to **Slab**.                                                                                                                                                                                 |
| **Foundation Height / First Floor Height** | Optional                | Used for determining depth of water within a structure.        | Defaults: **Basement = 4 ft**, **Crawlspace = (unspecified)**, **Pier = 5 ft**, **Fill = 3 ft**, **Slab = 1 ft**, **Pile/Wall = 8 ft**. Adjustments may be applied for pre- and post-FIRM structures. |
| **Basement Type**                          | Optional                | Used for determining damage function.                          | Defaults to **No Basement**.                                                                                                                                                                          |
| **Content Insurance Deductible**           | Optional                | Not used for loss calculations.                                | None.                                                                                                                                                                                                 |
| **Content Insurance Limit**                | Optional                | Not used for loss calculations.                                | None.                                                                                                                                                                                                 |
| **Building Insurance Deductible**          | Optional                | Not used for loss calculations.                                | None.                                                                                                                                                                                                 |
| **Building Insurance Limit**               | Optional                | Not used for loss calculations.                                | None.                                                                                                                                                                                                 |
