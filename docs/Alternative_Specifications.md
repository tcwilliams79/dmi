# DMI Alternative Specifications Guide

**Version**: 0.1.9  
**Last Updated**: December 2024

---

## Overview

The Distributional Misery Index (DMI) baseline specification uses:
- **Inflation**: CPI-U headline inflation (all items)
- **Labor Slack**: U-3 unemployment rate (official unemployment)

This document describes two alternative specifications that provide complementary perspectives for sensitivity analysis and research applications.

---

## Alternative 1: U-6 Unemployment

### Methodology

**Baseline**: U-3 unemployment (unemployed, actively seeking work)  
**Alternative**: U-6 unemployment (U-3 + underemployed + marginally attached)

The U-6 measure includes:
1. Unemployed workers (U-3 definition)
2. **Discouraged workers** (want work, stopped searching)
3. **Marginally attached** (want work, available, not actively searching)
4. **Part-time for economic reasons** (want full-time, involuntarily part-time)

**BLS Series ID**: `LNS13327709`

### When to Use

**U-6 is more appropriate when**:
- Analyzing recessions with high underemployment (e.g., Great Recession 2008-2009)
- Labor market shows slack beyond traditional unemployment (e.g., COVID-19 recovery)
- Interested in broader economic distress beyond job loss

**Example**: During the 2020 COVID recession, U-3 peaked at ~14.8% while U-6 reached ~22.9%, better capturing the full extent of labor market disruption.

### Results (November 2024)

| Measure | Rate | DMI (Q1) | DMI (Q5) | Avg DMI |
|---------|------|----------|----------|---------|
| **U-3 (Baseline)** | 4.2% | 6.85 | 6.65 | 6.77 |
| **U-6 (Alternative)** | 7.7% | 10.38 | 10.15 | 10.27 |
| **Difference** | +3.5pp | +3.53 | +3.50 | +3.50 |

**Observation**: U-6 DMI is consistently ~3.5 points higher, proportional to the broader measure of labor market slack.

### Interpretation Guidance

- **U-6 DMI values are NOT directly comparable to U-3 DMI values**
- Use U-6 for **relative comparisons** across time periods or income groups
- The U-6 vs U-3 gap size itself is informative (larger gap = more underemployment)

---

## Alternative 2: Core CPI

### Methodology

**Baseline**: CPI-U headline (all 8 major expenditure categories)  
**Alternative**: Core CPI (excluding food and beverages)

Core CPI excludes:
- **Food and beverages** (`CPI_FOOD_BEVERAGES`)

Core CPI provides a measure of underlying inflation, excluding the most volatile category.

> **Note**: This is a simplified core measure. The BLS publishes an official "core CPI" series (`CUSR0000SA0L1E`) that excludes both food and energy. Future versions may incorporate the official series.

### When to Use

**Core CPI is more appropriate when**:
- Assessing persistent vs transitory inflation
- Food/energy price shocks are temporary
- Comparing periods with vastly different commodity price volatility

**Example**: If food prices spike due to a drought or supply shock, core CPI DMI helps isolate underlying inflation pressure.

### Results (November 2024)

#### Inflation Comparison

| Quintile | Headline Inflation | Core Inflation | Difference | Food Impact |
|----------|-------------------|----------------|------------|-------------|
| **Q1** | 2.68% | 2.83% | +0.15pp | Lower |
| **Q2** | 2.65% | 2.78% | +0.13pp | Lower |
| **Q3** | 2.55% | 2.64% | +0.09pp | Lower |
| **Q4** | 2.51% | 2.59% | +0.08pp | Lower |
| **Q5** | 2.45% | 2.48% | +0.03pp | Similar |

**Observation**: In November 2024, food prices inflated *slower* than core items (by ~0.1-0.15pp for lower quintiles). This means food was actually dampening headline inflation.

#### DMI Comparison

| Quintile | Headline DMI | Core DMI | Difference |
|----------|--------------|----------|------------|
| **Q1** | 6.88 | 7.03 | +0.15 |
| **Q2** | 6.85 | 6.98 | +0.13 |
| **Q3** | 6.75 | 6.84 | +0.09 |
| **Q4** | 6.71 | 6.79 | +0.08 |
| **Q5** | 6.65 | 6.68 | +0.03 |
| **Average** | 6.77 | 6.90 | +0.13 |

**Observation**: Core and headline DMI are very close (±0.15 points). Food volatility has minimal impact on overall DMI in this period.

### Interpretation Guidance

- **Small differences** (<0.5 points): Food price volatility is not driving DMI differences
- **Large differences** (>1.0 points): Food prices significantly diverging from core inflation
- **Lower-income sensitivity**: Q1 shows larger difference (+0.15) than Q5 (+0.03) because food is a larger budget share

---

## Comparison Table

| Dimension | Baseline (U-3, Headline) | U-6 Alternative | Core CPI Alternative |
|-----------|-------------------------|-----------------|---------------------|
| **Labor Slack** | U-3 unemployment | U-6 unemployment | U-3 unemployment |
| **Inflation** | Headline CPI (all items) | Headline CPI | Core CPI (ex-food) |
| **Use Case** | General-purpose, official | Broader labor distress | Underlying inflation |
| **Typical Difference** | - | +3-4 points | ±0.5 points |
| **Best For** | Monitoring, policy | Recessions, underemployment | Volatility analysis |

---

## Historical Context (If Available)

> **Future Enhancement**: Run backfill scripts for U-6 and Core alternatives to generate historical time series (2011-2024). This would enable:
> - Correlation analysis across specifications
> - Identification of periods where alternatives diverge significantly
> - Validation that specification choice doesn't fundamentally alter conclusions

---

## Technical Notes

### Weight Renormalization (Core CPI)

When excluding food, weights are renormalized so each quintile's weights sum to 1.0:

```
New Weight = Original Weight / (Sum of Non-Food Weights)
```

**Example (Q1)**:
- Original food weight: 0.3109 (31.09%)
- Remaining weights sum: 0.6891
- Renormalized: Each non-food weight multiplied by 1/0.6891 ≈ 1.4510

This ensures inflation contributions still sum to the total.

### Data Availability

- **U-3**: Monthly data available 1948-present
- **U-6**: Monthly data available 1994-present (limits historical backfill to 1994+)
- **Core CPI**: Depends on category-level CPI data availability

---

## Recommendations

### For Researchers

1. **Report all three specifications** when:
   - Publishing academic work
   - Periods of high volatility (2020-2022)
   - Analyzing recessions

2. **Use U-6** when:
   - Labor market has significant underemployment
   - Comparing across business cycles
   - Validating U-3 results

3. **Use Core CPI** when:
   - Food/energy shocks are temporary
   - Analyzing monetary policy impacts
   - Testing robustness to volatile components

### For Public Communication

1. **Lead with baseline (U-3, Headline)** for:
   - Monthly updates
   - Press releases
   - Dashboard visualizations

2. **Note alternatives in footnotes** to:
   - Signal methodological rigor
   - Provide context for unusual periods
   - Link to this documentation for details

### For Policy Analysis

1. **U-6 provides early warning** of:
   - Hidden labor market slack
   - Divergence between official unemployment and economic reality

2. **Compare U-6 vs U-3 gap** over time:
   - Narrowing gap = labor market tightening genuinely
   - Widening gap = underemployment increasing

3. **Core CPI isolates persistent inflation**:
   - If Core DMI >> Headline DMI → Food deflation masking underlying pressure
   - If Core DMI << Headline DMI → Food inflation driving headline

---

## Generating Alternative Specifications

### U-6 Alternative

```bash
# Compute DMI using U-6 unemployment
./venv/bin/python -m scripts.compute_dmi_u6

# Output: data/outputs/dmi_release_2024-11_u6.json
```

### Core CPI Alternative

```bash
# Compute DMI using Core CPI (ex-food)
./venv/bin/python -m scripts.compute_dmi_core

# Output: data/outputs/dmi_release_2024-11_core.json
```

Both scripts automatically generate comparison reports vs baseline.

---

## Limitations

1. **No U-6 historical backfill yet**: U-6 only available 1994+, limits long-term comparisons

2. **Simplified Core measure**: Excludes only food, not energy sub-components. Official BLS core CPI would be more comprehensive.

3. **CE weights unchanged**: Alternatives use same 2023 CE weights. If food budget shares changed significantly, core CPI weights should ideally be re-estimated.

4. **No statistical testing**: Differences are reported without significance tests. For research, bootstrap confidence intervals recommended.

---

## Future Enhancements (v0.2.0+)

1. **Official BLS Core CPI series** (CUSR0000SA0L1E) instead of manual exclusion
2. **Energy sub-category exclusion** for more comprehensive core measure
3. **Historical backfill** for both alternatives (1994-2024 for U-6)
4. **Bootstrap confidence intervals** showing when differences are statistically significant
5. **Core-specific CE weights** (re-estimate weights excluding food expenditures)

---

## References

- **U-6 Definition**: BLS Labor Force Statistics, Table A-15
- **Core CPI**: Federal Reserve uses core CPI for inflation targeting
- **Series IDs**: 
  - U-3: `LNS14000000`
  - U-6: `LNS13327709`
  - Headline CPI: See `registry/series_catalog_v0_1.json`

---

**Questions?** See methodology documentation or contact [maintainer].
