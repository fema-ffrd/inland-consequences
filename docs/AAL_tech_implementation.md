# Average Annualized Loss (AAL) Technical Implementation

The inland consequence methodology computes Average Annualized Loss (AAL) using a numerical integration approach consistent with the method implemented in FEMA’s Hazus Program. The recommended implementation leverages the AAL calculation code developed for **SPHERE**, which is directly adapted from the Hazus Riemann sum formulation. This approach does not require a fixed set or number of return periods; instead, it operates on all available modeled frequencies and loss estimates provided by the user.

______________________________________________________________________

## AAL Calculation Method

The AAL is calculated using a discrete Riemann sum that integrates the loss–exceedance relationship across all provided return periods. The function below shows the reference implementation adapted from the Hazus Technical Manual. It expects:

**Inputs:**

- `in_rpnames`: a sorted (ascending) list of return periods
- `in_losses`: a list of loss values corresponding to each return period

The function returns a single numeric AAL value.

```python
#Formula adapted from Hazus Technical Manual 

# IN: 

#   in_rpnames = SORTED (ascending) list of return periods that pair sequentially with in_losses 

#             in_losses = list of losses that pair sequentially with in_rpnames 

# OUT: 

#   numeric value representing adjusted loss 

def calc_aal(in_rpnames, in_losses): 

    SumAnnLoss = 0 

    for i in range(len(in_losses)): 

        if i == (len(in_losses) - 1): 

            SumAnnLoss += (1 / in_rpnames[i]) * (in_losses[i]) 

        else: 

            SumAnnLoss += ((1 / in_rpnames[i]) - (1 / in_rpnames[i + 1])) * (((in_losses[i]) + (in_losses[i + 1])) / 2) 

    return SumAnnLoss 
```

This formulation treats each return-period pair as a point on the loss-exceedance curve and computes the integrated area beneath the curve.

______________________________________________________________________

## Truncation Option

The methodology supports two AAL calculation modes: non-truncated (default) and truncated.

### Non-Truncated AAL (Default, 0)

- Includes all provided return periods, even those with $0 loss.

- When the lowest-frequency return period has $0 loss, the $0 value is averaged with the next nonzero period.

  *Example:*

  - 50-year loss = $0
  - 100-year loss = $1,200
  - Average used in integration = (0 + 1,200) / 2 = **$600**

This follows the Hazus approach and provides a more conservative AAL estimate.

### Truncated AAL (1)

- Excludes the $0-loss return period from the summation.
- This approach aligns with the GoConsequences implementation.
- Generally produces lower AAL values, particularly when few frequencies are supplied.

Users should select the truncation setting based on analysis goals, regulatory requirements, or consistency with other modeling frameworks.

______________________________________________________________________

## Minimum Return Period Requirements

To ensure stable and interpretable AAL results, the tool should require at least three return periods. While the Riemann sum method can operate with fewer, accuracy improves substantially as more frequencies are included, particularly higher-frequency (smaller return period) events. Loss estimates become more reliable with a greater number of return periods; therefore, for best results, users should provide as many frequencies as possible across the full range of the hazard.

Future enhancements may include tooltip guidance on selecting appropriate return periods and automated detection of return periods from file names. However, the current implementation requires users to enter all return period values explicitly.
