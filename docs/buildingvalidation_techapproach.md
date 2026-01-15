# Building Inventory Validation Flags Technical Approach

The building Inventory validation flags are intended to identify structures with attributes that are often, but not always, associated with potential data issues. The validation logic is informed by review of the FFRD Duwamish study results and other recent analyses. The purpose of these flags is to guide user review rather than to automatically invalidate or correct inventory records. All flags are advisory in nature, and the approach is designed to preserve continuity of loss modeling so that results remain available even when a flag is present.

## Occupancy-Based Area and Valuation Review

One component of the validation evaluates building area and valuation consistency relative to the assigned occupancy type. Structures are compared against expected square footage ranges derived from the Hazus hzSqftFactors table. When a structure’s reported area exceeds five times the expected value for its occupancy type, the structure is flagged for review. This condition may indicate an incorrect occupancy assignment, an error in reported building area, or atypical building characteristics. When triggered, the user is notified that the structure has an unusually large area or valuation for the assigned occupancy type and that review of the occupancy type assignment or building area may be warranted. No automated corrections are applied as part of this check.

## Story Count Consistency by Occupancy Type

Another validation assesses consistency between the number of stories assigned to a structure and its occupancy type. Using guidance from the Hazus Inventory Technical Manual, structures are flagged when the reported number of stories is unusual for the assigned occupancy. Certain occupancy types are not typically associated with mid- or high-rise construction, particularly those exceeding three stories, while others are rarely associated with high-rise construction exceeding seven stories. When these thresholds are exceeded, the structure is flagged and the user is advised that the story count is unusual for the assigned occupancy type and should be reviewed. This validation is intended to prompt review of either the story count or the occupancy assignment, recognizing that legitimate exceptions may exist.

## Special Handling for RES1 Structures

Residential single-family structures (RES1) are handled as a special case within the story count validation. RES1 structures with more than three stories are flagged, as this configuration is uncommon within the Hazus framework. To ensure that loss estimates remain available, loss calculations assume a maximum of three stories for RES1 structures while retaining the original story count in the inventory for reporting and review purposes. The user-facing message communicates both the unusual nature of the attribute and the modeling assumption applied for loss estimation.

## Foundation Type and Flood Zone Consistency

Foundation type assignments are also evaluated for consistency with flood zone and location. Structures are flagged when the assigned foundation type is atypical for the mapped flood zone, such as basements located within V-zones. These conditions may indicate misclassification, legacy data artifacts, or localized exceptions and therefore warrant user review. At this stage, no automated changes are applied to foundation attributes; instead, the condition is surfaced through an advisory flag. This validation logic is designed to be extensible, with future enhancements anticipated to address additional scenarios such as post-FIRM basements within the Special Flood Hazard Area.

## Outputs and Use of Validation Flags

Each validation condition produces a discrete flag that is stored as a non-blocking indicator and accompanied by plain-language guidance for the user. Flags are intended to improve transparency and support informed review without interrupting downstream loss modeling workflows unless explicitly noted. Collectively, these validation checks provide a structured and extensible framework for improving inventory quality while maintaining analytical continuity.
