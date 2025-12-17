# DMI — CE Weights & CPI Granularity Decision Rubric (v0.1)

**Version:** 0.1.0  
**Last updated:** 2025-12-16  

This rubric is a *governance and engineering* aid for deciding:

1) **How to produce expenditure weights** w(g,c):  
   - **Option A:** BLS **published CE tables** (fast, v0.1 default)  
   - **Option B:** **CE PUMD** microdata processor (flexible, complex; v0.2+)

2) **How fine the CPI category universe should be** for the inflation component π(g,r,t):  
   - **Option 1:** **Major groups** (fast, robust, v0.1 default)  
   - **Option 2:** **ELI-level** (more detail, more plumbing)  
   - **Option 3:** Below ELI (rarely worth it early; only with strong justification)

The intent is to minimize *future technical debt* by making “upgrade paths” explicit and testable.

---

## A. Weight source decision: CE Tables vs CE PUMD

### A1. Option A — CE Published Tables (v0.1 default)

**What it is**  
Use BLS CE calendar-year *mean item share* tables by income quintile/decile, and map CE table rows into the CPI category universe via a pinned mapping artifact.

**Why it’s attractive for v0.1**
- Fast to implement; stable formats (XLSX tables)
- Easy to audit (public tables; simple extraction rules)
- Good enough to demonstrate the DMI idea and UX
- Lower compliance risk: fewer moving parts, fewer opportunities for silent errors

**Known limitations**
- Annual weights; limited stratifications (income before taxes by quintile/decile)
- Taxonomy mismatch (CE table labels ≠ CPI categories); must use an approximation mapping
- Limited ability to re-cut groups (e.g., age × income, renters vs owners, region)

**Use this when**
- You want a credible public MVP quickly
- You can tolerate “major group” inflation decomposition for v0.1
- You’re optimizing for reproducibility and auditability over flexibility

---

### A2. Option B — CE PUMD Processor (v0.2+ path)

**What it is**  
Process CE Interview + Diary microdata (hundreds of thousands of consumer units across files) to compute spending shares by arbitrary groups, mapped via UCC→ELI concordances into CPI categories.

**Why it’s powerful**
- Flexible grouping (income definition variants, demographics, geography proxies)
- Better category alignment potential (UCC→ELI→CPI)
- Enables variance estimation / uncertainty bands using replicate weights

**Why it’s expensive**
- High implementation complexity (file joins, replicate weights, imputation rules)
- Mapping complexity (UCC lines don’t cleanly map to CPI categories)
- Much higher QA burden and governance requirements

**Use this when**
- You need custom groups that tables cannot provide
- You want to support a finer CPI universe (e.g., ELI) with strong mapping fidelity
- You’re ready to invest in a mature QA + reproducibility harness

---

### A3. Weight-source upgrade “go/no-go” checklist

Move from **CE Tables → CE PUMD** only when *all* of these are true:

**Governance**
- [ ] A written, versioned PUMD methodology note exists (inputs, joins, exclusions, grouping definition)
- [ ] A pinned crosswalk artifact exists (UCC→ELI and ELI→CPI category_id), with checksums
- [ ] A clear “vintage change policy” is defined for the weights pipeline (annual updates and revisions)

**Data QA maturity**
- [ ] End-to-end unit tests covering at least one historical year with known published benchmarks
- [ ] Reconciliation checks: PUMD-derived major-group shares approximately match CE tables within expected tolerance (documented)
- [ ] Excluded share is tracked and bounded (e.g., excluded_share < 5% for major-group universe), or explicitly justified

**Operational readiness**
- [ ] Pipeline runtime + storage costs are acceptable for monthly releases
- [ ] Failure modes are well-defined (what fails publish vs what warns)
- [ ] You can reproduce a release from raw snapshots without manual steps

---

## B. CPI granularity decision: Major Groups vs ELI

### B1. Option 1 — CPI Major Groups (v0.1 default)

**Strengths**
- Stable, interpretable story (“Food”, “Housing”, “Transportation”, …)
- High coverage and consistent monthly availability for national CPI
- Lower taxonomy mismatch with CE tables (still imperfect, but manageable)

**Weakness**
- Coarse decomposition; may hide within-category offsets (e.g., rent vs owners’ equivalent rent)

**Default recommendation for v0.1**
- Compute and report at major groups.

---

### B2. Option 2 — CPI ELI-level categories (future)

**What you gain**
- Better “what moved this month” narratives (more diagnostic power)
- Potentially less aggregation bias in π(g,r,t)

**What you risk**
- Increased missingness / uneven coverage for subnational CPI
- Higher mapping complexity (weights must match ELI universe)
- More volatile group differences (noise vs signal) if weights are noisy

**Use ELI-level computation when**
- You have weights that natively map to ELI (usually requires PUMD or a very strong published-table mapping)
- Your QA suite can enforce category coverage and contributions identity at the ELI level
- You keep reporting stable via rollups (next section)

---

### B3. Make the retrofit easy: compute categories vs reporting categories

To make future CPI granularity upgrades low-friction:

1) **Keep the calculator category-agnostic**  
   - No hard-coded “Food/Housing/etc.” logic inside the math
   - Inputs are (category_id × period × geo) CPI levels and (group_id × category_id) weights

2) **Pin a category registry now**  
   - `category_registry_v0_1.json`: category_id, label, level, parent_category_id, universe membership

3) **Pin a reporting-views mapping now**  
   - `category_reporting_views_v0_1.json`: maps *computation* categories to *reporting* categories  
   - v0.1 uses identity mapping; v0.2+ can compute at ELI and roll up to major groups for reporting

4) **Pin crosswalk artifacts with checksums**  
   - Swap-in upgrades become: “new crosswalk + new weights + new series set”, not code changes

---

## C. Combined decision tree (practical)

**If you are staying on CE tables for weights (v0.1):**
- Prefer **major-group CPI** computation.
- You *can* add modest CPI refinements later, but keep reporting stable.

**If you want ELI CPI computation:**
- Strongly prefer moving to **PUMD-derived weights**, or accept clearly documented mapping approximations plus higher excluded_share.

**If you want subnational DMI (states/metros):**
- Start with **subnational slack + national CPI proxy** (explicitly flagged).
- Only publish subnational inflation when CPI category coverage is full and frequency-compatible per geo_inflation_policy.

---

## D. What to decide now (to avoid technical debt)

Recommended “do now” commitments (already aligned with the v0.1 spec choices):

- **Publish gate default:** FAIL on weights vintage changes unless explicitly approved  
  *But*: generate an internal backfill candidate + diff report for review.

- **Slack time alignment default:** same_reference_month_required (fail publish if not satisfiable)  
  Keep latest_available_not_after only for unpublished exploration.

- **Registries and pinning:**  
  - geo_registry (namespaced geo_id + stable geo_level enum)  
  - category_registry (hierarchy + universes)  
  - reporting views (compute vs report separation)  
  - crosswalk/mapping artifacts with version + checksum

- **QA invariants (category-granularity invariant):**  
  - weights sum to 1 per group (after exclusions/renormalization)  
  - weights non-negative  
  - category coverage completeness for the computation universe  
  - excluded share explicitly tracked  
  - contributions sum to π (within tolerance)

These choices keep v0.1 simple while making v0.2+ upgrades mostly a *data swap + QA expansion* exercise rather than a rewrite.
