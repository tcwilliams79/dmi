# DMI v0.1.9 Specification

**Version**: 0.1.9 (Draft)  
**Date**: 2025-12-17  
**Builds on**: v0.1.8 (Complete implementation)  
**Focus**: Research Tool + Public Communication

---

## Goals

**A) Research Tool**: Methodological rigor, transparency, reproducibility  
**B) Public Communication**: Accessibility, automation, historical context

---

## Scope

### **1. Automation & Production Readiness**

#### 1.1 GitHub Actions Workflow
**File**: `.github/workflows/monthly_dmi.yml`

**Trigger**: 
- Manual (for testing)
- Scheduled: 15th of each month (after BLS CPI release)

**Steps**:
1. Fetch latest CPI data (current month)
2. Fetch latest U-3 unemployment
3. Check if CE weights need update (annual)
4. Compute DMI for reference period
5. Run QA validation (8 checks)
6. Generate QA report
7. Create PR with:
   - New DMI output JSON
   - QA report
   - Updated time series
8. Require manual approval before merge
9. On merge: Deploy to Vercel

**Why**: Monthly indicator needs monthly automation.

#### 1.2 Error Handling & Resilience
**Files**: All `dmi_pipeline/agents/*.py`

**Enhancements**:
- Retry logic with exponential backoff (BLS API failures)
- Rate limit handling (max 500 calls/day for registered API key)
- Graceful degradation (warn but continue if non-critical data missing)
- Structured logging (JSON logs for debugging)
- Email/Slack notifications on failures

**Why**: Production systems must handle failures gracefully.

---

### **2. Historical Backfill (2010-2024)**

#### 2.1 Backfill Script
**File**: `scripts/backfill_historical.py`

**Features**:
- Compute DMI for all months from Jan 2010 to Nov 2024
- Use vintage-appropriate CE weights:
  - 2010-2012: Use 2010 CE weights
  - 2013-2014: Use 2013 CE weights
  - 2015-2016: Use 2015 CE weights
  - ... (2-year vintages per conservative policy)
- Document weights vintage used for each period
- Generate QA reports for each period
- Save outputs to `data/outputs/published/historical/`

#### 2.2 Time Series Dataset
**File**: `data/outputs/published/dmi_timeseries_2010_2024.json`

**Schema**:
```json
{
  "series_id": "DMI_NATIONAL_QUINTILE",
  "start_period": "2010-01",
  "end_period": "2024-11",
  "observations": [
    {
      "period": "2010-01",
      "group_id": "Q1",
      "dmi": 8.45,
      "inflation": 2.3,
      "slack": 9.7,
      "weights_vintage": 2010
    },
    ...
  ]
}
```

**Why**: One month isn't useful. Users need context and trends.

---

### **3. Enhanced Visualization**

#### 3.1 Time Series Charts
**File**: `web/index.html` (enhanced)

**New Charts**:
1. **DMI Over Time** (2010-2024)
   - Line chart: 5 lines (Q1-Q5)
   - Recession shading (2020, 2008-2009)
   - Hover: Show exact values + context

2. **Quintile Divergence**
   - Area chart: Q5-Q1 dispersion over time
   - Shows when inequality in economic pressure widened/narrowed

3. **Inflation Decomposition**
   - Stacked bar: Category contributions to total inflation
   - By quintile
   - Animated transitions

4. **Unemployment Context**
   - Dual-axis: DMI + U-3 rate
   - Show correlation

**Technology**: Chart.js or Plotly.js (lightweight, no React needed)

#### 3.2 Comparative Analysis
**Features**:
- "Current vs Historical Average" indicator
- "Percentile ranking" (e.g., Nov 2024 DMI is 35th percentile historically)
- Recession comparisons (vs 2020, vs 2008)

**Why**: Help users interpret "is 6.85 high or low?"

---

### **4. Alternative Specifications (Research Rigor)**

#### 4.1 U-6 Unemployment
**File**: `dmi_pipeline/agents/bls_api_client.py` (enhanced)

**Implementation**:
- Fetch U-6 (unemployment + underemployment) series: LNS13327709
- Compute alternative DMI using U-6 instead of U-3
- Save as: `dmi_release_2024-11_u6.json`
- Document differences in QA report

**Expectation**: U-6 DMI will be ~3-4 points higher than U-3 DMI

#### 4.2 Core CPI (Excluding Food & Energy)
**Implementation**:
- Add core CPI series to catalog
- Compute alternative inflation excluding CPI_FOOD_BEVERAGES and energy components
- Save as: `dmi_release_2024-11_core.json`

**Why**: Sensitivity to volatile categories

#### 4.3 Alternatives Documentation
**File**: `docs/Alternative_Specifications.md`

**Content**:
- Table comparing baseline vs alternatives
- When each alternative is more appropriate
- Historical correlation analysis
- Not recommending one over another - transparency about choices

---

### **5. Confidence Intervals (Research Rigor)**

#### 5.1 CE Sampling Error Propagation
**File**: `dmi_calculator/uncertainty.py` (new)

**Method**:
- Extract standard errors from CE published tables
- Propagate through weight aggregation
- Bootstrap simulation (1000 draws)
- Report 95% confidence intervals

**Output Enhancement**:
```json
{
  "group_id": "Q1",
  "dmi": 6.85,
  "dmi_ci_lower": 6.72,
  "dmi_ci_upper": 6.98,
  "inflation": 2.65,
  "inflation_ci_lower": 2.59,
  "inflation_ci_upper": 2.71
}
```

#### 5.2 Visualization
- Error bars on time series charts
- Shaded confidence bands
- Note: Only for weights uncertainty, not CPI (CPI is census-based)

**Why**: Transparent about statistical precision

---

### **6. Enhanced Documentation**

#### 6.1 Methodology Note (Academic-Style)
**File**: `docs/DMI_Methodology_v0.1.9.pdf`

**Sections**:
1. Introduction & Motivation
2. Data Sources
3. Calculation Methodology
4. Alternative Specifications
5. Uncertainty Quantification
6. Validation & QA Process
7. Historical Trends
8. Limitations
9. References

**Why**: Citable for researchers

#### 6.2 API Documentation
**File**: `docs/API.md`

**Even if no live API yet**, document the **data format** for programmatic use:
- How to download JSON files
- Schema documentation
- Example Python/R/JavaScript usage

---

## Implementation Phases

### Phase A: Automation & Historical (Week 1)
- [ ] GitHub Actions workflow
- [ ] Historical backfill script
- [ ] Error handling improvements
- [ ] Time series dataset generation

**Estimated**: 8-10 hours

### Phase B: Visualization & Alternatives (Week 2)
- [ ] Time series charts (Chart.js)
- [ ] Comparative analysis
- [ ] U-6 alternative specification
- [ ] Core CPI alternative

**Estimated**: 6-8 hours

### Phase C: Uncertainty & Documentation (Week 3)
- [ ] Confidence interval implementation
- [ ] Methodology note (PDF)
- [ ] API documentation
- [ ] Alternative specs documentation

**Estimated**: 8-10 hours

**Total Estimated Effort**: 22-28 hours

---

## Success Criteria

**Research Tool**:
- ✅ Confidence intervals reported
- ✅ 2+ alternative specifications available
- ✅ Methodology note published
- ✅ All calculations reproducible

**Public Communication**:
- ✅ Automated monthly updates
- ✅ Historical data (2010-2024) available
- ✅ Interactive time series charts
- ✅ Clear context ("is this high or low?")

---

## Deferred to v0.2.0

**Subnational Expansion**:
- State-level DMI
- Metro-area DMI
- Regional price parity adjustments

**Reason**: Requires significant new data infrastructure (state CE weights, regional CPI)

**Live API**:
- RESTful endpoints
- Rate limiting
- Authentication

**Reason**: Current static JSON sufficient for v0.1.9

---

## Next Steps

1. **Review this spec** - Does this balance A+B correctly?
2. **Prioritize** - Which phase to start with?
3. **Set timeline** - When do you want v0.1.9 complete?

**Recommendation**: Start with **Phase A** (Automation + Historical) - this provides immediate value and unblocks visualization work.
