# DMI Plain-English Monthly Summary Generator Specification

## Objective

Enhance the `compute-dmi` pipeline so that it generates a short, plain-English monthly summary for each DMI release.

The summary must be:
- deterministic, not LLM-dependent
- nonpartisan
- descriptive rather than causal
- understandable by policymakers, staff, journalists, and engaged citizens
- stable in tone across months
- safe to publish automatically

The generator must replace the current placeholder summary text in both:
- `releases.json`
- `latest.json`

## Current manifest context

Current release manifests have this shape at the top level:

- `schema_version`
- `generated_at`
- `current_release_id`
- `releases` (array)

Each release currently includes:
- `release_id`
- `data_through_label`
- `published_at`
- `status`
- `methodology_version`
- `summary`
- `urls`
- `metrics`

`metrics` currently includes:
- `dmi_median`
- `dmi_stress`
- `income_pressure_gap`
- `unemployment`

Example current values:
- 2026-02: `dmi_median=6.8540624815102555`, `dmi_stress=7.009919860204779`, `income_pressure_gap=0.2779924571955972`, `unemployment=4.4`
- 2026-01: `dmi_median=6.68309620289141`, `dmi_stress=6.860113040349798`, `income_pressure_gap=0.29578362843907247`, `unemployment=4.3`
- 2025-12: `dmi_median=7.060246136848632`, `dmi_stress=7.182520631286057`, `income_pressure_gap=0.21631985239523033`, `unemployment=4.4`

## Required implementation

### 1. Add a deterministic summary generator

Create a pure function that takes:
- the current release record
- the immediately prior release record, if present
- optional contributor information, if available

and returns:
- `summary_facts` (structured facts used to drive wording)
- `summary` (final human-readable text)

Suggested function signature:

```python
def build_release_summary(
    current_release: dict,
    prior_release: dict | None = None,
    contributor_context: dict | None = None,
) -> tuple[dict, str]:
    ...
```

Use type hints and unit-testable logic.

### 2. Add `summary_facts` to each release record

Add a new optional field at the release level:

```json
"summary_facts": {
  "overall_direction": "rose_modestly",
  "median_delta_mom": 0.17,
  "stress_delta_mom": 0.15,
  "gap_delta_mom": -0.02,
  "unemployment_delta_mom": 0.1,
  "gap_direction": "narrowed_slightly",
  "lower_income_more_pressure": true,
  "highest_pressure_quintile": "Q1",
  "lowest_pressure_quintile": "Q5",
  "top_contributors_q1": ["housing", "food", "medical care"]
}
```

This field is for transparency/debugging and can be consumed later by site code or release-note templates.

### 3. Keep `summary` as a plain string

The existing `summary` field must remain present and should now contain the generated text.

### 4. Update both manifest outputs

When the release pipeline runs, it must write:
- updated `summary` and `summary_facts` into the corresponding release inside `releases.json`
- updated `summary` and `summary_facts` into `latest.json` for the current release

## Summary content rules

### Target length

Generate exactly 2 or 3 sentences.
Preferred length: 35 to 75 words.

### Tone constraints

The summary must:
- avoid partisan language
- avoid blame or causal attribution
- avoid loaded terms like “inequality worsened,” “squeezed,” “working families,” “pain,” “burdened by policymakers,” etc.
- avoid forecasting
- avoid advice
- avoid policy recommendations
- avoid the term “dispersion”
- use the public-facing metric name “Income Pressure Gap”

The summary may:
- describe changes month over month
- describe whether lower-income households continue to face more pressure than higher-income households
- describe whether the gap widened, narrowed, or was little changed
- mention top contributors if available

### Allowed vocabulary

Use simple, neutral wording such as:
- rose
- fell
- edged up
- edged down
- little changed
- widened slightly
- narrowed slightly
- remained elevated
- continued to face more pressure
- typical pressure
- peak pressure
- bottom income fifth
- top income fifth

### Forbidden wording

Do not use:
- “inequality”
- “hardship worsened”
- “economic pain”
- “working families”
- “the economy punished”
- “policy failure”
- “stagflation”
- “crisis”
- “class divide”
- “suffering”
- “distributional injustice”

## Deterministic algorithm

### Inputs used

At minimum, use:
- current `dmi_median`
- current `dmi_stress`
- current `income_pressure_gap`
- current `unemployment`
- prior values for same fields when prior release exists

Optionally use:
- contributor context such as top contributors for Q1

### Derived deltas

Compute:
- `median_delta_mom = current.dmi_median - prior.dmi_median`
- `stress_delta_mom = current.dmi_stress - prior.dmi_stress`
- `gap_delta_mom = current.income_pressure_gap - prior.income_pressure_gap`
- `unemployment_delta_mom = current.unemployment - prior.unemployment`

Round only for display, not internal comparison.

### Classification thresholds

Use these thresholds exactly unless there is a strong implementation reason to centralize them as config constants.

#### For DMI Median and DMI Stress direction labels

For absolute delta `abs(x)`:

- `< 0.05` => `little_changed`
- `>= 0.05 and < 0.15` => `edged_up` / `edged_down`
- `>= 0.15 and < 0.30` => `rose_modestly` / `fell_modestly`
- `>= 0.30` => `rose_sharply` / `fell_sharply`

Determine overall direction primarily from `median_delta_mom`.
Use `stress_delta_mom` as supporting text, not the primary classifier.

#### For Income Pressure Gap

For absolute delta `abs(gap_delta_mom)`:

- `< 0.02` => `gap_little_changed`
- `>= 0.02 and < 0.08` => `gap_widened_slightly` / `gap_narrowed_slightly`
- `>= 0.08` => `gap_widened_materially` / `gap_narrowed_materially`

Also compute:
- `lower_income_more_pressure = current.income_pressure_gap > 0`
- `higher_income_more_pressure = current.income_pressure_gap < 0`
- `pressure_similar_across_bottom_top = abs(current.income_pressure_gap) < 0.02`

#### For unemployment wording

For absolute delta `abs(unemployment_delta_mom)`:

- `< 0.1` => `unemployment_little_changed`
- `>= 0.1 and < 0.3` => `unemployment_edged_up` / `unemployment_edged_down`
- `>= 0.3` => `unemployment_rose_noticeably` / `unemployment_fell_noticeably`

## Summary sentence templates

Implement summary rendering using templates, not free-form generation.

### Preferred structure

#### Sentence 1: overall movement
Describe the movement in typical pressure, based on DMI Median.

Examples:
- `Economic pressure rose modestly in {data_through_label}.`
- `Economic pressure was little changed in {data_through_label}.`
- `Economic pressure edged down in {data_through_label}.`

#### Sentence 2: distributional pattern
Describe the bottom-vs-top pattern using Income Pressure Gap.

Examples:
- `Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap narrowed slightly from the prior month.`
- `Pressure remained uneven across incomes, with the bottom income fifth facing more pressure than the top income fifth.`
- `The Income Pressure Gap widened slightly, indicating a less even distribution of pressure across the bottom and top income fifths.`

#### Sentence 3: optional concrete detail
Use either unemployment change or contributor detail.

Priority:
1. if contributor info exists, mention top contributors for Q1
2. else mention unemployment movement if there is a prior release
3. else omit third sentence

Examples:
- `Housing remained the largest contributor for the bottom income fifth.`
- `For the bottom income fifth, the main contributors remained housing, food, and medical care.`
- `The labor-market backdrop also softened slightly, with unemployment edging up to 4.4%.`

### Fallback behavior

If there is no prior release:
- do not mention month-over-month change
- produce a static descriptive summary

Fallback example:
`The February 2026 release shows higher measured pressure for lower-income households than for higher-income households. The current dashboard reports a DMI Median of 6.85, a DMI Stress reading of 7.01, and an Income Pressure Gap of 0.28.`

## Contributor support

If contributor data is available from the pipeline, support:
- `top_contributors_q1`: list[str]
- optionally `top_contributors_q5`: list[str]

If `top_contributors_q1` exists and has at least 1 item, the summary generator should use it in sentence 3.

Formatting rules:
- 1 item => `"Housing remained the largest contributor for the bottom income fifth."`
- 2 items => `"The main contributors for the bottom income fifth were housing and food."`
- 3+ items => `"For the bottom income fifth, the main contributors remained housing, food, and medical care."`

Do not mention contributors if contributor data is absent.

## Required schema update

Bump manifest schema version from `1.0.0` to `1.1.0`.

Add optional release-level fields:
- `summary_facts`
- `notes` (if not already present in branch)
- optional `urls.dashboard`
- optional `urls.repo`

Do not break existing consumers.

## Output examples

### Example expected summary for 2026-02 using current data and 2026-01 as prior

Given:
- DMI Median rises from `6.6831` to `6.8541`
- DMI Stress rises from `6.8601` to `7.0099`
- Income Pressure Gap falls from `0.2958` to `0.2780`
- unemployment rises from `4.3` to `4.4`

Expected acceptable summary:
`Economic pressure rose modestly in February 2026. Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap narrowed slightly from the prior month. The labor-market backdrop also softened slightly, with unemployment edging up to 4.4%.`

Minor wording variation is acceptable if it remains deterministic and consistent with the thresholds.

### Example expected `summary_facts` for 2026-02

```json
{
  "overall_direction": "rose_modestly",
  "median_delta_mom": 0.17096627861884536,
  "stress_delta_mom": 0.14980681985498082,
  "gap_delta_mom": -0.017791171243475257,
  "unemployment_delta_mom": 0.1,
  "gap_direction": "gap_little_changed",
  "lower_income_more_pressure": true
}
```

Note: because `abs(gap_delta_mom) = 0.01779 < 0.02`, the strict threshold classifies the gap as `little_changed`. If you want the wording to say `narrowed slightly` instead, adjust the threshold boundary accordingly and document that choice in code comments. The implementation must be internally consistent.

## Acceptance criteria

1. `compute-dmi` writes a non-placeholder `summary` for each release.
2. `compute-dmi` writes `summary_facts` for each release.
3. `releases.json` and `latest.json` are both updated.
4. The generator works with 1 release present and with multiple releases present.
5. No LLM or API call is required.
6. Output is deterministic across repeated runs with identical input.
7. The implementation includes unit tests for the threshold logic and summary rendering.
8. The summary never uses forbidden wording.
9. The summary never references unavailable fields.
10. Existing manifest consumers do not break.

## Tests to implement

At minimum, add unit tests for:

### Classification tests
- median delta `0.00` => `little_changed`
- median delta `0.07` => `edged_up`
- median delta `0.18` => `rose_modestly`
- median delta `0.40` => `rose_sharply`
- gap delta `-0.01` => `gap_little_changed`
- gap delta `-0.05` => `gap_narrowed_slightly`
- gap delta `0.10` => `gap_widened_materially`

### Rendering tests
- no prior release => fallback 2-sentence summary
- prior release, no contributors => 2 or 3 sentences using unemployment if present
- prior release, contributors present => contributor sentence used
- negative Income Pressure Gap => wording reflects higher-income households facing more pressure
- near-zero Income Pressure Gap => wording says pressure was felt more similarly across bottom and top income fifths

### Regression test using current known manifests
Use the current 2026-02 and 2026-01 records and assert:
- summary is not placeholder text
- summary mentions February 2026
- summary mentions Income Pressure Gap
- summary_facts deltas match computed values within float tolerance

## Implementation notes

- Use small pure helper functions.
- Centralize threshold constants.
- Keep prose templates in one place.
- Do not hardcode release IDs.
- Prefer clarity over cleverness.
- Add inline comments explaining why the tone is constrained.
- Keep summary generation independent from WordPress/site code.

## Deliverables

1. Updated summary generation code in `compute-dmi`
2. Updated manifest writer
3. Updated schema version and schema docs if present
4. Unit tests
5. Brief README note describing how summaries are generated
