# DMI v0.1 — Implementation Checklist (v0.1.8)

**Purpose:** This is a developer-facing checklist to implement the DMI v0.1 pipeline in a way that is robust, reproducible, and compatible with the v0.1 output contract (Vercel static publish).  
**Spec package revision:** v0.1.8  
**Last updated:** 2025-12-17  

---

## A. CE Tables → Weights (robust XLSX parsing)

### A1. Retrieval + raw integrity
- [ ] Download the CE decile (preferred) and quintile (fallback) XLSX using the URL templates in `ce_weights_policy_v0_1.json`.
- [ ] Save **exact raw XLSX** under `data/raw/` and record:
  - [ ] `retrieval_timestamp`
  - [ ] `source_url`
  - [ ] SHA256 checksum

### A2. Structural validation (before extraction)
Implement the structural validation checks described in `ce_weights_policy_v0_1.json → structural_validation`.

- [ ] Check: expected CE item labels are discoverable (`expected_ce_item_labels`)
- [ ] Check: **Mean → Share row pairing** exists and “Share row immediately after Mean row” rule holds
- [ ] Check: group column count sanity (decile=10 or quintile=5; ignore “All consumer units” if present)
- [ ] Soft warn: share range sanity (typical 0..100 for percent shares)

Failure behavior:
- [ ] On any HARD_FAIL: stop the pipeline (do not publish) and raise a clear error naming `check_id`
- [ ] Emit parse diagnostics (sheet name + header + first N rows/cols) to:
  - `data/outputs/internal/review_packets/{run_id}/ce_table_parse_diagnostics.json` (suggested path)

### A3. Extraction + mapping
- [ ] Extract shares from the Share rows only (do not use Mean rows for weights)
- [ ] Convert CE shares into weights (0..1) deterministically (document percent→fraction conversion)
- [ ] Apply the pinned mapping artifact `registry/artifacts/ce_table_to_cpi_mapping_v0_1.json`
- [ ] Track **excluded_share** explicitly and renormalize included weights (per policy)

### A4. Weights QA
- [ ] All weights non-negative (post-renormalization)
- [ ] Weights sum to 1.0 ± tolerance per group
- [ ] Excluded share is stored (even if 0.0)

---

## B. CPI category coverage (hard requirement for published releases)

### B1. Category universe
- [ ] Load `registry/category_registry_v0_1.json`
- [ ] Filter to universe_id = `CPI_MAJOR_GROUPS_V0_1` (expected 8 categories)

### B2. Coverage validation (hard check)
For reference period *t* and horizon_months (default 12):
- [ ] CPI level data exists for all categories for *t*
- [ ] CPI level data exists for all categories for *(t − horizon_months)*
- [ ] If any category-period is missing: FAIL publish gate and include examples in QA report

---

## C. Slack alignment (published vs research)

Published mode:
- [ ] Enforce `same_reference_month_required` (slack period == inflation reference period)
- [ ] If slack is missing for reference month: FAIL publish gate

Research mode (unpublished):
- [ ] Allow `latest_available_not_after` only if explicitly configured
- [ ] Must emit flags + metadata (requested_period, slack_period_used)

---

## D. Weights vintage change gate + review packet (no auto publish)

Trigger:
- [ ] Detect `weights_year` change vs prior published `release_metadata.json`

Default action (v0.1):
- [ ] FAIL publish gate

Internal assist artifacts:
- [ ] Generate `data/outputs/internal/review_packets/{run_id}/weights_vintage_review_packet.json`
- [ ] Candidate recomputation:
  - [ ] Default (v0.1.8): recompute **previous published reference period** using new weights_year (hold CPI + slack constant for that period)
- [ ] Deterministic diff summary (minimum):
  - [ ] `delta_dmi_by_group`
  - [ ] `delta_inflation_by_group`
  - [ ] `delta_dispersion_metrics`
- [ ] Never auto-publish candidate outputs; publishing requires explicit approval recorded in release metadata

---

## E. Publisher: output contract compliance + schema validation

### E1. Output contract prevalidation
- [ ] Load `registry/output_contract_v0_1.json`
- [ ] Pre-check that you can produce **all required published artifacts** before writing the release directory
- [ ] Avoid partially-written releases (prefer staging output to a temp dir, then atomic move)

### E2. Schema validation (jsonschema)
- [ ] Validate required JSON artifacts against schemas before copying into `published/`:
  - [ ] `dmi_release.json` vs `schemas/dmi_output.schema.json`
  - [ ] `qa_report.json` vs `schemas/qa_report.schema.json`
  - [ ] `release_metadata.json` vs `schemas/release_metadata.schema.json`
  - [ ] `weights_by_group.json` vs `schemas/weights.schema.json`
  - [ ] Internal-only (when triggered): `weights_vintage_review_packet.json` vs `schemas/weights_vintage_review_packet.schema.json`

### E3. Release metadata completeness
- [ ] `release_metadata.json.outputs[]` lists every published file with checksum (where feasible)
- [ ] Policy decision objects are present (geo inflation decision, slack decision, weights decision)
- [ ] `qa.status` matches QA report

### E4. Latest aliases
- [ ] Create/refresh `data/outputs/published/latest/*` per contract
- [ ] Ensure compatibility alias `latest/dmi_us_quintile_latest.json` exists

---

## F. Automated tests (minimum)

- [ ] Unit tests: calculator math (π, slack, DMI formula)
- [ ] Unit tests: CE table extraction on a known year XLSX fixture
- [ ] Unit tests: category coverage validator (missing category triggers FAIL)
- [ ] Unit tests: schema validation utility (valid/invalid cases)
- [ ] Integration test: end-to-end pipeline on fixture data produces all contract-required artifacts

