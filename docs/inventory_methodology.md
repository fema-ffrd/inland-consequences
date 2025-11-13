# Inventory Methodology  

The **Consequences Solution** is designed to operate out of the box with two predefined national inventories: the **National Structures Inventory (NSI)** and the **Milliman Market Basket Data**. Users may also integrate their own **custom structure inventories** by defining a corresponding **JSON schema**. For additional guidance on configuring and loading custom inventories, refer to the [**Technical Implementation Documentation**](building_inventories.md).  
______________________________________________________________________

## Inventory Dataset Format  

The **Consequences Solution** currently accepts input inventory datasets in **point geometry** format, representing the location of each structure to be analyzed. Supported input formats include **Comma-Separated Values (.csv)**, **Esri Shapefile (.shp)**, **File Geodatabase (.gdb)**, and **GeoPackage (.gpkg)**. Each record should include the **required attribute fields** used in the loss calculations, and all spatial data should be stored in a **projected coordinate system** appropriate for the analysis extent. Using point-based inputs ensures compatibility with the **consequence modeling workflow** and enables efficient spatial joins with hazard and inventory datasets.   

______________________________________________________________________

## Inventory Attributes Used in Analysis  

The following attributes are used in the **Consequences Solution** loss calculations. While providing all recommended fields from the input inventory dataset ensures more accurate loss estimates, missing attributes will automatically be populated with **default values**. However, reliance on these defaults may reduce the precision of results.  

Loss calculations for **inland** and **coastal** areas require different sets of input attributes.
**Table 1** outlines the required inventory inputs for inland loss calculations, while **Table 4** details the corresponding inputs for coastal loss calculations.  
______________________________________________________________________

### **Table 1. Inventory Input Data Requirements for Inland Consequence Modeling**  

| **Input Data** | **Required / Optional** | **Purpose** | **Default Process If Data Not Provided** |
|----------------|--------------------------|--------------|------------------------------------------|
| **Geometry** | Required | Locational geometry is required for spatial analysis. | None, required input. If CSV option added, alt and long fields would replace this. |
| **Unique ID** | Required | Used for identifying the structure throughout analysis. | None, required input. |
| **Occupancy Type** | Optional | Primary use is for the selection of depth damage functions in analysis. A secondary use is to provide default values if square footage/area attribution is unavailable. | Defaults to **RES1**. |
| **Building Value** | Required | Used for the calculation of structural loss. | None, required input. See *Hazus Inventory Manual* if guidance is required. |
| **Content Value** | Optional | Used for the calculation of content loss. | If not provided, structures will be assigned a default content value based on a percentage of the building value for each Occupancy Type following the Hazus Methodology. See **Table 3** for percentages by occupancy type. |
| **Number of Stories** | Optional | Used for the assignment of depth damage functions in analysis. | Defaults to **1 story**. Important for **RES1** when available, as DDFs differ significantly. Cannot exceed **3** for RES1. |
| **Area / Square Footage** | Optional | Used for assigning depth damage functions and for calculations such as debris and income-related losses. | If not provided, structures will be assigned a default area based on typical square footage by Occupancy Type from the *Hazus Methodology* (see **Table 2**). |
| **General Building Type** | Optional | Used for assignment of flood-specific building type for inland analysis. | Defaults to **W (Wood)**. Hazus tract-level mapping schemes by occupancy type (*hzGenBldgScheme*) can be used to enhance inventories. |
| **Foundation Type** | Optional | Used for selecting the appropriate depth damage function. | Defaults to **Slab**. Hazus mapping schemes (also used by **NSI**) are available for users to enhance inventories. |
| **Foundation Height** | Optional | Used to determine depth of water within a structure. | Defaults: **Slab = 1 ft**, **Shallow = 3 ft**, **Pile = 8 ft**, **Basement = 4 ft**. Adjustments can be considered for pre- and post-FIRM structures. |
| **Foundation Type from Parcel Data** | Optional | Used, if available, to refine foundation type assignment. | -- |
| **Basement Type from Parcel Data** | Optional | Used, if available, to refine foundation type assignment. | -- |

______________________________________________________________________

### **Table 2. Hazus Methodology for Default Building Square Footage by Occupancy Type**  

| **Occupancy Type** | **Square Footage** |
|--------------------|-------------------:|
| AGR1 | 30,000 |
| COM1 | 110,000 |
| COM10 | 145,000 |
| COM2 | 30,000 |
| COM3 | 10,000 |
| COM4 | 80,000 |
| COM5 | 4,100 |
| COM6 | 55,000 |
| COM7 | 7,000 |
| COM8 | 5,000 |
| COM9 | 12,000 |
| EDU1 | 130,000 |
| EDU2 | 50,000 |
| GOV1 | 11,000 |
| GOV2 | 11,000 |
| IND1 | 30,000 |
| IND2 | 30,000 |
| IND3 | 45,000 |
| IND4 | 45,000 |
| IND5 | 45,000 |
| IND6 | 30,000 |
| REL1 | 17,000 |
| RES1 | 1,800 |
| RES2 | 1,475 |
| RES3A | 2,200 |
| RES3B | 4,400 |
| RES3C | 8,000 |
| RES3D | 15,000 |
| RES3E | 40,000 |
| RES3F | 80,000 |
| RES4 | 135,000 |
| RES5 | 25,000 |
| RES6 | 25,000 |

______________________________________________________________________

### **Table 3. Content Value as Percent of Building Value by Occupancy Type**  

| **Occupancy Type** | **Content Value (%)** |
|--------------------|----------------------:|
| AGR1 | 100% |
| COM1 | 100% |
| COM10 | 50% |
| COM2 | 100% |
| COM3 | 100% |
| COM4 | 100% |
| COM5 | 100% |
| COM6 | 150% |
| COM7 | 150% |
| COM8 | 100% |
| COM9 | 100% |
| EDU1 | 100% |
| EDU2 | 150% |
| GOV1 | 100% |
| GOV2 | 150% |
| IND1 | 150% |
| IND2 | 150% |
| IND3 | 150% |
| IND4 | 150% |
| IND5 | 150% |
| IND6 | 100% |
| REL1 | 100% |
| RES1 | 50% |
| RES2 | 50% |
| RES3A | 50% |
| RES3B | 50% |
| RES3C | 50% |
| RES3D | 50% |
| RES3E | 50% |
| RES3F | 50% |
| RES4 | 50% |
| RES5 | 50% |
| RES6 | 50% |

______________________________________________________________________

### **Table 4. Inventory Input Data Requirements for Coastal Consequence Modeling**  

| **Input Data** | **Required / Optional** | **Purpose** | **Default Process** |
|----------------|--------------------------|--------------|----------------------|
| **Geometry** | Required | Locational geometry is required for spatial analysis. | None, required input. |
| **Unique ID** | Required | Used for identifying the structure throughout analysis. | None, required input. |
| **Building Value** | Required | Used for the calculation of structural loss. | None, required input. |
| **Ground Elevation** | Required | Used to determine depth of water in structure. | None, required input. |
| **Number of Stories** | Optional | Used for the assignment of depth damage functions in analysis. | Defaults to **1 story** if data not provided. |
| **Foundation Type** | Optional | Used for the selection of the depth damage function. | Defaults to **Slab**. |
| **Foundation Height / First Floor Height** | Optional | Used for determining depth of water within a structure. | Defaults: **Basement = 4 ft**, **Crawlspace = (unspecified)**, **Pier = 5 ft**, **Fill = 3 ft**, **Slab = 1 ft**, **Pile/Wall = 8 ft**. Adjustments may be applied for pre- and post-FIRM structures. |
| **Basement Type** | Optional | Used for determining damage function. | Defaults to **No Basement**. |
| **Content Insurance Deductible** | Optional | Not used for loss calculations. | None. |
| **Content Insurance Limit** | Optional | Not used for loss calculations. | None. |
| **Building Insurance Deductible** | Optional | Not used for loss calculations. | None. |
| **Building Insurance Limit** | Optional | Not used for loss calculations. | None. |

______________________________________________________________________

## National Structures Inventory  

The **National Structures Inventory (NSI)**, developed by the **U.S. Army Corps of Engineers (USACE)**, is a nationwide database of structures across the 50 U.S. states. At present, the NSI does not include coverage for U.S. territories. The publicly available NSI dataset provided many of the key fields used in this analysis; however, it is important to note that **building** and **contents values** are reported as **depreciated values** rather than full replacement costs. Full technical documentation for the NSI is available on the [**USACE NSI Technical Documentation page**](https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/technical-documentation).  

USACE also maintains a **restricted version** of the NSI accessible to federal users, which contains additional attributes derived from parcel data and other proprietary sources.  

To support national hazard risk assessments, **FEMA** has developed an **enhanced internal version** of the NSI that extends coverage to the **District of Columbia**, **Puerto Rico**, the **U.S. Virgin Islands**, and **Pacific Territories**. This FEMA-enhanced dataset applies **full replacement values** consistent with the *Hazus 7.0 Inventory Technical Manual* and resolves several known data quality issues identified in the public NSI.  

The following tables list the NSI attributes referenced in this analysis.  
- **Table 5** summarizes attributes from the public USACE NSI.  
- **Table 6** lists those from the FEMA-enhanced NSI.  
  Each table identifies the analysis attribute, the NSI field name, data type, and notes describing the attribute specific to NSI.  

______________________________________________________________________

### **Table 5. NSI Public Data Attributes for Analysis**

| **Analysis Attribute** | **NSI Field Name** | **Data Type** | **Notes** |
|------------------------|--------------------|----------------|------------|
| Geometry | Shape | Point | -- |
| Unique ID | fid | Object ID | -- |
| Occupancy Type | occtype | String | -- |
| Building Value | val_struct | Double | Depreciated replacement value |
| Content Value | val_cont | Double | Depreciated replacement value |
| Number of Stories | num_story | Double | -- |
| Area / Square Footage | sqft | Double | -- |
| General Building Type | bldgtype | String | Building type of the structure, typically associated with exterior wall material and used for structural stability analyses (e.g., M = Masonry, W = Wood, H = Manufactured, S = Steel) |
| Foundation Type | found_type | String | Type of foundation (C = Crawl, B = Basement, S = Slab, P = Pier, I = Pile, F = Fill, W = Solid Wall) |
| Foundation Height | found_ht | Double | Height of the foundation, in feet, above ground elevation |
| Ground Elevation | ground_elv | Double | Ground elevation (in feet, NAVD88) at the structure determined using the USGS National Elevation Dataset (NED) |

______________________________________________________________________

### **Table 6. NSI FEMA-Enhanced Version Data Attributes for Analysis**

| **Analysis Attribute** | **NSI Field Name** | **Data Type** | **Notes** |
|------------------------|--------------------|----------------|------------|
| Geometry | Shape | Point | -- |
| Unique ID | OBJECTID | Object ID | -- |
| Occupancy Type | OCCTYPE | String | -- |
| Building Value | Hazus_Building_Values | Double | Full replacement value |
| Content Value | Hazus_Content_Values | Double | Full replacement value |
| Number of Stories | NUM_STORY | Double | -- |
| Area / Square Footage | SQFT | Double | -- |
| General Building Type | GENERALBUILDINGTYPE | String | Building type of the structure, typically associated with exterior wall material and used for structural stability analyses (e.g., M = Masonry, W = Wood, H = Manufactured, S = Steel) |
| Foundation Type | FNDTYPE | String | Type of foundation (C = Crawl, B = Basement, S = Slab, P = Pier, I = Pile, F = Fill, W = Solid Wall) |
| Foundation Height | FOUND_HT | Double | Height of the foundation, in feet, above ground elevation |
| Foundation Type from Parcel Data | P_FNDTYPE | String | See **Table 7**. “P” tables are private attributes and license restricted. |
| Basement Type from Parcel Data | P_BSMNT | String | Type of basement from parcel data (B = Basement (Unknown Details), U = Unfinished Basement, F = Finished Basement, N = None (No Basement)). “P” attributes are private data with restricted licensing. |
| Ground Elevation | *Missing* | *Missing* | *Preprocessing required by user for calculating coastal losses.* |

______________________________________________________________________

### **Table 7. NSI P_FNDTYPE Parcel Value Mapping**

| **Parcel Basement Value** | **Parcel Basement Description** | **Mapped to NSI Basement Value** | **Mapped Description** |
|----------------------------|----------------------------------|----------------------------------|--------------------------|
| B | Basement | B | Basement (Unknown Details) |
| U | Unfinished Basement | U | Unfinished Basement |
| I | Improved Basement (Finished) | F | Finished Basement |
| N | No Basement | N | None |
| F | Full Basement | B | Basement (Unknown Details) |
| P | Partial Basement | B | Basement (Unknown Details) |
| L | Daylight; Partial | B | Basement (Unknown Details) |
| D | Daylight; Full | B | Basement (Unknown Details) |
| Y | Yes | B | Basement (Unknown Details) |

______________________________________________________________________

## Milliman Market Baskets

The **Milliman Market Baskets** were developed by **Milliman, Inc.** to support **FEMA’s Risk Rating 2.0 initiative**. Milliman created Market Baskets for all U.S. states and territories to provide a representative sample of **single-family homes (RES1)** used in the development of rating factors. Market Basket locations were derived primarily from **CoreLogic ParcelPoint** data, supplemented with **U.S. Census** and **National Hydrography Dataset (NHD)** information, and refined through **extensive quality control** to ensure accuracy and realistic spatial distribution.  

Three categories of data, referred to as **“books”**, were created from the Market Baskets:  
1. **Uniform Book** – Each property assigned identical structural and coverage characteristics, allowing geographic variability to be analyzed independently.  
1. **Uncorrelated Market Basket** – Contains randomized property and policy characteristics not correlated with geography; *foundation type* and *first-floor height* remain linked to prevent implausible combinations.  
1. **Correlated Market Basket (Inforce Dataset)** – Joined with FEMA policy data (GFE access required); attributes are correlated to reflect realistic joint distributions and align with observed **parcel** and **NFIP exposure** data.  

**Table 8** describes the analysis attributes used across the Market Basket books. While the schema is consistent, each book imputes fields differently—**Uncorrelated** randomizes property and coverage attributes, whereas the **Inforce** dataset applies state-specific distributions to reflect actual conditions.  

______________________________________________________________________

### **Table 8. Milliman Data Attributes for Analysis**

| **Analysis Attribute** | **NSI Field Name** | **Data Type** | **Notes** |
|------------------------|--------------------|----------------|------------|
| Geometry | Shape | Point | -- |
| Unique ID | Location | String | -- |
| Occupancy Type | -- | -- | All points are **RES1** |
| Building Value | BLDG_VALUE | Long | Full replacement value |
| Building Insurance Deductible | BLDG_DED | Long | -- |
| Building Insurance Limit | BLDG_LIMIT | Long | -- |
| Content Value | CNT_VALUE | Long | Full replacement value |
| Content Insurance Deductible | CNT_DED | Long | -- |
| Content Insurance Limit | CNT_LIMIT | Long | -- |
| Number of Stories | NUM_STORIE | Long | -- |
| Area / Square Footage | -- | -- | Default area for **RES1** based on *Hazus Methodology* (sqft = 1,800) |
| General Building Type | -- | -- | Default value = **W** |
| Foundation Type | foundation | Long | Foundation type (2 = basement; 4 = crawlspace; 6 = pier; 7 = fill or wall; 8 = slab; 9 = pile) |
| Foundation Height | FIRST_FLOO | Long | First floor height (feet above ground) |
| Basement Type | BasementFi | Long | Basement finish type (0 = no basement; 1 = unfinished basement; 2 = finished basement) |
| Ground Elevation | DEMft | Float | Digital Elevation Model (DEM) ground elevation (feet, NAVD88) |

______________________________________________________________________

The **Milliman Market Basket** datasets can be applied to both **coastal** and **inland** loss calculations, as they include the necessary structural, coverage, and geographic attributes to support modeling in either environment.
However, their use is limited to **single-family residential (RES1)** structures, as the Market Baskets were specifically developed for **Risk Rating 2.0**.
For more details, refer to the [**FEMA Risk Rating 2.0 Methodology and Data Appendix (2022)**](https://www.fema.gov/sites/default/files/documents/FEMA_Risk-Rating-2.0_Methodology-and-Data-Appendix__01-22.pdf).
