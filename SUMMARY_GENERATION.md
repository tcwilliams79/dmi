# DMI Summary Generation

The DMI pipeline automatically generates plain-English summaries for each release using deterministic logic based on the release metrics.

## How Summaries Are Generated

Summaries are created by the `build_release_summary()` function in `scripts/compute_dmi.py`, which:

1. Compares current release metrics to the immediately prior release (if available)
2. Classifies changes using predefined thresholds (e.g., changes < 0.05 are "little changed")
3. Constructs 2-3 sentence summaries using template phrases
4. Ensures neutral, non-causal language focused on descriptive changes

## Key Features

- **Deterministic**: Same inputs always produce the same output
- **Non-LLM**: Pure algorithmic generation, no AI models required
- **Constrained tone**: Avoids partisan, causal, or alarmist language
- **Metric-driven**: Based on DMI Median, DMI Stress, Income Pressure Gap, and unemployment changes

## Thresholds

- Little changed: < 0.05 (DMI), < 0.015 (Gap), < 0.1 (Unemployment)
- Edged: 0.05-0.15
- Modestly: 0.15-0.30
- Sharply: > 0.30

## Output

Each release includes:
- `summary`: Human-readable text (2-3 sentences)
- `summary_facts`: Structured data used for generation (for transparency/debugging)

Summaries are updated in both `releases.json` and `latest.json` during pipeline runs.