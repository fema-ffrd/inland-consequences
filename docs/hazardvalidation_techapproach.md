# Hazard Validation Flag Technical Approach

This approach defines a set of hazard-based validation flags intended to identify unusual or inconsistent hazard and loss characteristics at the structure level that may indicate potential issues with building location, hazard inputs, or damage function assignment. These conditions are often, but not always, associated with data anomalies and are intended to prompt user review rather than trigger automatic correction or exclusion. All flags are advisory in nature and are designed to support improved interpretability and confidence in hazard and loss outputs while maintaining continuity of downstream analyses.

## Structure-Level Depth and Velocity Anomalies

One component of the hazard validation focuses on identifying unusually high flood depths and velocities at or within structures for a given return period. For the 10-year return period, structures are flagged when flood depths in-structure exceed five feet or velocities exceed ten feet per second, as these conditions are uncommon for frequent events and may indicate erroneous building locations, spatial misalignment, or localized issues within the hazard data. For all other return periods, more conservative thresholds are applied, with structures flagged when depths exceed twenty feet in-structure or velocities exceed thirty feet per second. While these thresholds may be refined by return period in the future, they are intended to capture the majority of anomalous conditions without over-flagging typical high-hazard environments. When triggered, the user is notified that hazard parameters are unusually high and should be reviewed for potential location or hazard data anomalies.

From a combined hazard and loss perspective, unusually high depths or velocities occurring at or within structures, particularly for frequent return periods, are treated as strong indicators of potential issues with the underlying hazard data or structure placement. These conditions are surfaced through advisory flags to support targeted review.

## Loss Ratio Consistency Checks

Additional validation evaluates the consistency of modeled losses relative to exposed value. Structures are flagged when building or content loss ratios exceed 1.0, indicating modeled losses greater than 100 percent of the associated value. These conditions typically suggest issues with depth-damage function assignment, value attribution, or hazard inputs and warrant further review. No automatic adjustments are applied as part of this validation.

For frequent events, additional scrutiny is applied to loss severity. Structures with 10-year return period losses exceeding 50 percent of building or content value are flagged for review, as such high losses during frequent events often indicate erroneous building locations or anomalies in the hazard data. These flags are intended to draw attention to potentially unrealistic hazard–exposure interactions.

## Average Annual Loss Ratio Review

Average Annual Loss (AAL) ratios are also evaluated as part of the hazard validation framework. Structures with AAL loss ratios exceeding 10 percent are flagged for review, as unusually high AAL values may indicate persistent exposure to extreme hazard conditions, mislocated structures, or inconsistencies across return period hazard inputs. This validation supports identification of cases where aggregated loss behavior is inconsistent with expected hazard frequency and severity.

## Return Period Monotonicity and Uncertainty Consistency

The final hazard validation evaluates consistency of flood depths and velocities across return periods. Flood depths and velocities at a structure are expected to increase monotonically with increasing return period, following the sequence 10-, 20-, 50-, 100-, 200-, 500-, 1,000-, and 2,000-year events. Structures are flagged when this monotonic relationship is violated, as such patterns may indicate issues with hazard surface generation, interpolation artifacts, or uncertainty handling.

This validation extends to cases where uncertainty is applied. Minimum and maximum hazard values derived from uncertainty bounds are expected to preserve the same increasing relationship across return periods. For example, the minimum flood depth for the 2,000-year event, even when computed as mean minus standard deviation, should exceed the corresponding minimum for the 1,000-year event. Violations of this expectation are flagged for review to ensure internal consistency of probabilistic hazard inputs.

## Outputs and Use of Hazard Validation Flags

Each hazard validation condition produces a discrete, non-blocking flag accompanied by plain-language guidance indicating the nature of the anomaly and the recommended focus of review. Flags are advisory and are intended to support transparency, diagnostics, and informed quality assurance without interrupting loss modeling workflows. Collectively, these validations provide a structured framework for identifying potential hazard and loss inconsistencies while preserving analytical continuity.
