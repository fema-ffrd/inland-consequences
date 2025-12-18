# Inland Consquences Methodology

______________________________________________________________________

## Hazard Data Inputs

The inland consequence methodology relies on a set of core hazard layers that describe the depth (required), uncertainty (optional), velocity (optional), and duration (optional) of flooding at each location. These inputs collectively guide the selection of the appropriate depth-damage functions and determine the damage to the structure associated cost. While the methodology is designed for FEMA’s Future Flood Risk Data (FFRD) post-processed annual exceedance probably (AEP) flood depth rasters and their associated velocity, duration and uncertainty layers, it is designed to be flexible and can operate with any user-provided hazard data that meets the required formats. The sections below describe the role, requirements, and assumptions associated with each hazard input.

### Flood Depth

Flood depth rasters are the primary hazard input driving the inland consequence calculations and only required hazard input. The methodology is built to ingest FEMA’s post-processed AEP depth rasters for multiple return periods, but it is flexible enough to operate with any valid flood depth raster. Under normal use, the tool expects depth inputs for several AEPs, allowing annualized losses to be computed from a consistent hazard set. Users may modify the number of AEPs depending on the data available, however a minimum of three return periods is required to calculate average annualized loss. Depth values must be provided in units of feet.

The tool can also run in single-event mode by ingesting a single depth raster representing a historical or design event; in this configuration, the tool produces an event-specific loss rather than an annualized estimate.

At this time, the methodology does not ingest the full suite of FFRD Monte Carlo simulation rasters to compute annualized losses directly from the simulation ensemble; this capability is identified as a future enhancement.

### Flood Depth Uncertainty

Flood depth uncertainty rasters provide information on the variability of the predicted flood depth for each AEP. When supplied, these uncertainty layers allow the methodology to explore loss sensitivity and characterize uncertainty more explicitly within the loss calculation process. One uncertainty raster is expected per AEP return period, and the units mirror those of the depth rasters (feet). Although optional, these layers are recommended for users who want to evaluate the robustness of loss estimates or conduct probabilistic analyses. When uncertainty rasters are not provided, the methodology proceeds deterministically using the best-estimate depth values only.

### Flood Velocity

Velocity data support the classification of flood hazard peril and influence the selection of the appropriate depth-damage functions. When a velocity raster is provided, the methodology evaluates each structure’s exposure to high-velocity flow conditions. Velocities exceeding 5 feet per second are treated as high-velocity flooding and may result in the application of different or more severe DDFs. Values below this threshold are classified as low-velocity conditions. If a velocity raster is not supplied, the methodology defaults to assuming low-velocity flooding for all structures. More detail on how velocity interacts with DDF selection is provided in the *Flood Hazard Peril* section.

### Flood Duration

Flood duration rasters are used to determine whether structures are exposed to long-duration inundation, which can significantly affect building performance and loss outcomes. Duration values must be provided in hours, with exposures greater than 72 hours classified as long-duration flooding. This classification may influence which depth-damage functions are applied. When no duration raster is provided, the methodology assumes short-duration flooding for all structures. As with velocity, duration-based peril classification is further discussed in the *Flood Hazard Peril* section.

### File Types

Hazard data is compatible with existing file export formats such as GeoTIFFs and TIFFs, consistent with previous consequence solutions like the Hazus Flood Assessment Structure Tool (FAST) and early FFRD pilot outputs. However, because the final FFRD datasets and file formats are still being defined, additional support has also been implemented for cloud-optimized formats, including Zarr and Xarray-based readers.

______________________________________________________________________

## Depth-Damage Function (DDF) Assignment

The inland consequence methodology assigns depth-damage functions (DDFs) by integrating three key structural and hazard characteristics: foundation type, flood-specific building type, and flood hazard peril. These elements collectively determine how a structure is expected to perform under various flooding conditions and which DDF curve should be applied to calculate percent damage at a given inundation depth. The methodology follows the principles and thresholds developed through the OpenHazus initiative and is designed to maintain alignment with FEMA’s broader approach to flood consequence modeling.

### Foundation Type

Foundation type is a key structural attribute that influences how buildings respond to flooding and, in cases where foundation information is missing, helps determine the default flood condition applied during loss calculation. The methodology classifies foundations into four categories: Basement, Shallow, Slab, and Pile. Each foundation type is associated with an expected default foundation height when height information is not available in the structure inventory, Table 1.

**Table 1. Inland Foundation Types and Default Foundation Heights**

| Foundation Type | Default Foundation Height |
|-----------------|---------------------------|
| Basement | 2 ft |
| Pile | 8 ft |
| Shallow | 3 ft |
| Slab | 1 ft |

Based on NSI 2025 pre-release materials, an adjustment was made to the default basement foundation heights from 4 ft to 2 ft for alignment.

The consequence methodology is designed to natively support the NSI 2022 Public Version, NSI 2022 Private Version, and Milliman Market Basket datasets. For additional details on how foundation types are defined and derived within these inventories, refer to the [**Building Inventories Technical Implementation Documentation**](building_inventories.md).

### Flood-Specific Building Type (FLSBT)

The flood-specific building type (FLSBT) classification refines how structures are represented in the inland consequence methodology by incorporating building characteristics that more accurately capture flood vulnerability. This approach aligns the flood model with how other Hazus hazards—particularly the Hurricane (Wind) model—define buildings. Rather than relying solely on occupancy type and number of stories, the methodology also incorporates general building type (e.g., wood, masonry, concrete, steel, manufactured housing), resulting in a more nuanced representation of building performance under flood conditions.

General building type reflects the primary construction material and structural system, while the specific building type further differentiates structures based on occupancy and the actual number of stories. The use of explicit story counts—rather than generic low-, mid-, or high-rise categories—allows the methodology to take advantage of depth-damage functions developed specifically for 1-, 2-, and 3-story structures, which represent the majority of the building stock.

Table 2 represents the flood-specific building classes used to assign depth-damage functions.

**Table 2. Flood-Specific Building Type Classes**

| SBT Code | General Building Type | FLSBT Group | SBT Range | Description | Occupancy / Usage | Notes |
|---------|------------------------|-------------|-----------|-------------|--------------------|-------|
| WSFX | Wood | F Wood Group 1 | WSF001–WSF004 | Wood, single-family | RES1, RES3A / IRC | Assume pre-engineered |
| WMUHX | Wood | F Wood Group 2 | WMUH001–WMUH004 | Wood, multi-unit housing | RES3B–F, RES4–6 / IBC | Assume pre-engineered |
| WLRMX | Wood | F Wood Group 3 | WLRM001–WLRM002 | Wood, commercial strip mall | 1–2 story COM1, COM9 / IBC | Assume engineered |
| WLRIX | Wood | F Wood Group 4 | WLRI001–WLRI006 | Wood, industrial/warehouse | ≥3 story COM1, COM9; non-res / IBC | Assume engineered |
| MSFX | Masonry | F Masonry Group 1 | MSF001–MSF007 | Masonry, single-family | RES1, RES3A / IRC | Assume pre-engineered |
| MMUHX | Masonry | F Masonry Group 2 | MMUH001–MMUH007 | Masonry, multi-unit housing | RES3B / IBC | Assume pre-engineered |
| MLRMX | Masonry | F Masonry Group 3 | MLRM001–MLRM002 | Masonry, commercial strip mall | 1–2 story COM1, COM9 / IBC | Assume pre-engineered |
| MLRI | Masonry | F Masonry Group 4 | MLRI | Masonry industrial/warehouse | 1 story IND1, AGR1 / IBC | Assume pre-engineered |
| MERBX | Masonry | F Masonry Group 5 | MERB001–MERB030 | Masonry engineered residential | RES3C–F, RES4–6 / IBC | Assume engineered |
| MECBX | Masonry | F Masonry Group 6 | MECB001–MECB030 | Masonry engineered commercial | ≥3 story COM1, COM9; ≥2 story IND1, AGR1; others / IBC | Assume engineered |
| CSFX | Concrete | F Concrete Group 1 | CSF001–CSF040 | Concrete engineered single-family | RES1, RES3A / IRC | Assume engineered |
| CERBX | Concrete | F Concrete Group 2 | CERB001–CERB040 | Concrete engineered multifamily | RES3B–F, RES4–6 / IBC | Assume engineered |
| CECBX | Concrete | F Concrete Group 3 | CECB001–CECB040 | Concrete engineered commercial | All non-res / IBC | Assume engineered |
| SPMB | Steel | F Steel Group 1 | SPMB | Steel pre-engineered metal building | ≤4,000 sq ft COM1–2, IND1–6, AGR1 | Assume pre-engineered |
| SERBX | Steel | F Steel Group 2 | SERB001–SERB108 | Steel engineered residential | RES1, RES3–6 / IRC & IBC | Assume engineered |
| SECBX | Steel | F Steel Group 3 | SECB001–SECB108 | Steel engineered commercial | >4,000 sq ft COM1–2, IND1–6, AGR1; all non-res / IBC | Assume engineered |
| MH | Manufactured Home | F MH Group 1 | MH | Manufactured home | RES2 | Assume pre-engineered |

This classification system allows the assigned depth-damage functions reflect differences in structural material, design practice, occupancy, and building height. By grounding the hazard model in detailed structural attributes, the methodology better captures the diversity of building performance observed across the U.S. building stock and improves the accuracy and relevance of resulting loss estimates.

If the number of stories in the inventory exceeds the maximum permitted for its general building type, occupancy, and square footage combination, the structure will be flagged for review and assigned the FLSBT corresponding to the highest allowable number of stories for that configuration.

### Hazard Peril

Hazard peril describes the specific flood conditions a structure is exposed to and is a critical determinant of how damage progresses during an event. Different flood processes—such as long-duration inundation or high-velocity flow—impose distinct physical stresses on buildings, and selecting the correct peril ensures that the depth-damage function accurately reflects those conditions.

For inland (riverine) flooding, the methodology classifies hazard peril based on duration and velocity. Long-duration flooding is defined as inundation lasting 72 hours or more, consistent with thresholds used in USACE’s GoConsequences model. When duration data are unavailable, flooding is treated as short duration. Flow velocity is then evaluated to distinguish between low- and high-velocity conditions. High-velocity flooding is defined as flow ≥ 5 ft/s; values below this threshold are considered low velocity. If velocity data are not available, the methodology defaults to low-velocity conditions.

Each structure is assigned a single riverine flood peril based on the combination of duration and velocity characteristics. The riverine peril types used in this methodology are shown in Table 3.

**Table 3. Riverine Flood Peril Descriptions**

| Flood Peril | Description |
|-------------|-------------|
| RLS | Riverine, Low Velocity, Short Duration |
| RHS | Riverine, High Velocity, Short Duration |
| RLL | Riverine, Low Velocity, Long Duration |
| RHL | Riverine, High Velocity, Long Duration |

### DDF Assignment

Once foundation type, flood-specific building type, and hazard peril are assigned, the methodology uses lookup tables consistent with OpenHazus to determine the appropriate depth-damage function (DDF). The assigned DDF determines percent damage at each depth and forms the basis for building-, contents-, and inventory-level loss calculations.

This workflow continues to evolve under the OpenHazus innovation account and the Natural Hazard Risk Assessment Program. The modular structure allows for future enhancements such as probabilistic DDF selection and integration with expanded hazard datasets.

______________________________________________________________________

## Loss Calculations

The inland consequence methodology calculates flood losses by combining structure-level attributes, hazard inputs, and depth-damage functions (DDFs) to estimate expected damages to buildings, contents, and inventory. The process begins by determining the flood depth at each structure and proceeds through percent-damage estimation, loss calculation, and annualization across all modeled return periods.

### Determining Depth in Structure

Loss calculations begin by spatially intersecting each structure with the flood depth raster to determine the depth at the structure location. Structures with 0 or negative depths at structure will not have losses calculated as these represent dry structures. The methodology then subtracts the foundation height from this value to compute the depth in structure, which represents the depth of water relative to the occupied or finished interior of the building. For some foundation negative depths in structure will result in losses, such as finished basement where you would see damage below the first-floor.

### Applying Depth-Damage Functions

Each building component (structure, contents, and inventory) has its own DDF ID and corresponding depth-damage curve. After we determine the water depth inside the structure, we use each DDF ID to look up the expected percent damage for that component. Depth-damage curves report damage at fixed depth intervals (for example, every 0.5 or 1 foot). To estimate damage at the exact water depth, the methodology interpolates between the curve’s points, producing a smooth, continuous estimate. The result is three separate percent-damage values—one each for structure, contents, and inventory—representing how much of each component is expected to be lost at that water depth.

The monetary loss for each component (structure, content and inventory) is calculated by multiplying the percent damage by its corresponding valuation amount (structure valuation, content valuation and inventory valuation).

This process is followed for each return period to produce estimated losses for each return period included in the hazard dataset. For single return periods events, results are provided after this loss calculation. For multiple return periods events, an average annualized loss is calculated.

### Average Annualized Loss (AAL)

After losses are computed across all available return periods, the inland consequence methodology derives the Average Annualized Loss (AAL), which represents the long-term expected loss per year. The AAL is calculated using a Riemann sum numerical integration approach, consistent with the methodology employed in FEMA’s Hazus Program. Table 4 illustrates this method, in which the inland consequence solution computes annual losses for eight probabilistic return periods (RPs). The annual probability of each event is calculated as 1/RP, and differential probabilities are obtained by subtracting adjacent annual occurrence probabilities.

The average loss for each interval is then calculated by averaging the annual losses associated with the corresponding return periods, as shown in the “average losses” column. The AAL is obtained by summing the products of each average loss and its associated differential probability, resulting in a single annualized estimate of expected flood-related losses.

In this approach, each pair of return-period losses and their associated frequencies is treated as a point along a continuous loss-exceedance curve. As illustrated in Figure1, by summing the areas of rectangles or trapezoids formed between adjacent points, the Riemann sum integrates across the full range of flood frequencies to produce the annualized loss.

**Table 4 Average Annualized Building Loss Estimations**

| Return Period | Annual Probability | Differential Probability | Scenario Loss ($) | Average Loss Formula | Average Loss ($) | Annualized Loss ($) |
|---------------|--------------------|---------------------------|--------------------|-----------------------|-------------------|----------------------|
| 2,000 | 0.00050000 | 0.00050000 | $163,850 | L2000 | 163,850 | $82 |
| 1,000 | 0.00100000 | 0.00050000 | $163,850 | (L2000 + L1000) / 2 | 163,850 | $82 |
| 500 | 0.00200000 | 0.00100000 | $163,850 | (L1000 + L500) / 2 | 163,850 | $164 |
| 200 | 0.00500000 | 0.00300000 | $163,850 | (L500 + L200) / 2 | 163,850 | $492 |
| 100 | 0.01000000 | 0.00500000 | $163,850 | (L200 + L100) / 2 | 163,850 | $819 |
| 50 | 0.02000000 | 0.01000000 | $163,850 | (L100 + L50) / 2 | 163,850 | $1,639 |
| 20 | 0.05000000 | 0.03000000 | $163,850 | (L50 + L20) / 2 | 163,850 | $4,916 |
| 10 | 0.10000000 | 0.05000000 | $163,850 | (L20 + L10) / 2 | 163,850 | $8,193 |
| **Total** | | | | | | **$16,385** |

**Figure 1 Illustration of Estimating Area of Loss Curve Based on Input Return periods Using Riemann Sums Method**

![Illustration of Estimating Area of Loss Curve Based on Input Return periods Using](images/AAL.png)

A greater number and wider range of modeled return periods yield a more complete and representative loss curve. A minimum of three return periods is required to compute AAL, though including additional frequencies improves accuracy. Contractor research indicates that using approximately 22 return periods offers an effective balance, capturing the loss curve with high fidelity while minimizing computational demands. However, final decision for FFRD surround the number periods is pending.

**Figure 2 PTS Contractor Research on the Recommendation for Identifying 22 return periods to represent the full Annual Exceedance Probability Curve**

![PTS Contractor Research on the Recommendation for Identifying 22 return periods to represent the full Annual Exceedance Probability Curve](images/AEP_Research.png)

______________________________________________________________________

## Uncertainty

TO DO

______________________________________________________________________

## Results

TO DO
