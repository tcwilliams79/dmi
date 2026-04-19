#!/usr/bin/env python3
"""
Compute and publish a DMI release for an explicit reference period.

This wrapper exists so scheduled and manually-triggered release runs honor the
reference period chosen by the workflow, rather than silently falling back to
"latest staged data available" behavior.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dmi_pipeline.agents.qa_validator import generate_qa_report, print_qa_summary
from scripts.compute_dmi import (
    build_release_summary,
    compute_dmi_for_period,
    export_csv_parquet,
    generate_release_note_html,
    load_cpi_data,
    load_slack_data,
    load_weights,
    save_dmi_output,
    save_release_note,
    update_health_json,
    update_latest_json,
    update_releases_json,
    update_timeseries_json,
)

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def staging_window_for_period(reference_period: str) -> tuple[int, int]:
    """Map a release period to the staged data file window that should contain it."""
    year_str, month_str = reference_period.split('-')
    year = int(year_str)
    month = int(month_str)

    if month >= 11:
        return year, year + 1
    return year - 1, year


def ensure_period_available(reference_period: str, cpi_df, slack_df) -> None:
    """Fail fast with a clear message if the requested period is not staged."""
    cpi_periods = sorted(cpi_df['period'].unique())
    slack_periods = sorted(slack_df['period'].unique())

    if reference_period not in cpi_periods:
        raise SystemExit(
            f"Requested reference period {reference_period} is not present in staged CPI data. "
            f"Latest staged CPI period: {cpi_periods[-1]}"
        )

    if reference_period not in slack_periods:
        raise SystemExit(
            f"Requested reference period {reference_period} is not present in staged slack data. "
            f"Latest staged slack period: {slack_periods[-1]}"
        )


def load_prior_release(reference_period: str):
    """Load the most recent prior release, excluding the target period if already present."""
    releases_path = Path("data/outputs/releases.json")
    if not releases_path.exists():
        return None

    with open(releases_path, 'r') as f:
        existing = json.load(f)

    if isinstance(existing, dict) and 'releases' in existing:
        releases = existing.get('releases', [])
    elif isinstance(existing, list):
        releases = existing
    else:
        releases = []

    releases = [r for r in releases if r.get('release_id') != reference_period]
    if not releases:
        return None

    releases.sort(key=lambda x: x['release_id'], reverse=True)
    return releases[0]


def build_metrics_payload(results: dict) -> dict:
    """Return the standardized metrics payload used across release artifacts."""
    return {
        'dmi_median': results['summary_metrics']['dmi_median'],
        'dmi_stress': results['summary_metrics']['dmi_stress'],
        'income_pressure_gap': results['summary_metrics']['dmi_income_pressure_gap'],
        'unemployment': results['dmi_by_group'][0]['slack'],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute and publish a DMI release for an explicit reference period."
    )
    parser.add_argument(
        'reference_period',
        help='Reference period to publish, in YYYY-MM format (for example 2026-03).',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reference_period = args.reference_period

    print("=" * 80)
    print("DMI Release Runner")
    print("=" * 80)
    print(f"Requested reference period: {reference_period}")

    start_year, end_year = staging_window_for_period(reference_period)

    weights_path = Path("data/curated/weights_by_group_2023.json")
    cpi_path = Path(f"data/staging/cpi_levels_{start_year}_{end_year}.json")
    slack_path = Path(f"data/staging/slack_u3_{start_year}_{end_year}.json")

    if not cpi_path.exists():
        raise SystemExit(f"Missing staged CPI file for {reference_period}: {cpi_path}")
    if not slack_path.exists():
        raise SystemExit(f"Missing staged slack file for {reference_period}: {slack_path}")

    print("\nLoading data...")
    weights_df = load_weights(weights_path)
    print(f"  ✓ Weights: {len(weights_df)} records")

    cpi_df = load_cpi_data(cpi_path)
    print(f"  ✓ CPI data: {len(cpi_df)} periods from {cpi_path.name}")

    slack_df = load_slack_data(slack_path)
    print(f"  ✓ Slack data: {len(slack_df)} periods from {slack_path.name}")

    ensure_period_available(reference_period, cpi_df, slack_df)

    print("\n" + "=" * 80)
    print(f"Computing release for explicit period {reference_period}")
    results = compute_dmi_for_period(
        cpi_df=cpi_df,
        weights_df=weights_df,
        slack_df=slack_df,
        reference_period=reference_period,
        alpha=0.5,
        scale_factor=2.0,
    )

    output_path = Path(f"data/outputs/dmi_release_{reference_period}.json")
    save_dmi_output(results, output_path)

    print("\n" + "=" * 80)
    print("Generating QA Report...")
    print("=" * 80)
    qa_report = generate_qa_report(
        dmi_output=results,
        cpi_data=cpi_df,
        weights_data=weights_df,
        slack_data=slack_df,
        output_path=Path(f"data/outputs/qa_report_{reference_period}.json"),
    )
    print_qa_summary(qa_report)

    print("\n" + "=" * 80)
    print("Creating CSV and Parquet files...")
    print("=" * 80)
    export_csv_parquet(results, reference_period)

    year, month = reference_period.split('-')
    current_release = {
        'release_id': reference_period,
        'data_through_label': f"{MONTH_NAMES[int(month) - 1]} {year}",
        'metrics': build_metrics_payload(results),
    }
    prior_release = load_prior_release(reference_period)
    summary_facts, summary = build_release_summary(current_release, prior_release)

    print("\n" + "=" * 80)
    print("Generating release note HTML...")
    print("=" * 80)
    release_html = generate_release_note_html(
        reference_period=reference_period,
        metrics=build_metrics_payload(results),
        summary=summary,
    )
    save_release_note(release_html, reference_period)

    print("\n" + "=" * 80)
    print("Updating release manifests...")
    print("=" * 80)
    metrics_payload = build_metrics_payload(results)
    update_releases_json(
        reference_period=reference_period,
        metrics=metrics_payload,
        summary=summary,
        summary_facts=summary_facts,
    )
    update_latest_json(
        reference_period=reference_period,
        metrics=metrics_payload,
        summary=summary,
        summary_facts=summary_facts,
    )
    update_health_json(reference_period)
    update_timeseries_json(reference_period)

    print("\n" + "=" * 80)
    print("DMI RELEASE SUMMARY")
    print("=" * 80)
    print(f"Period: {reference_period}")
    print(f"Computed at: {datetime.utcnow().isoformat()}Z")
    for record in results['dmi_by_group']:
        print(
            f"  {record['group_id']}: DMI={record['dmi']:6.2f}  "
            f"(inflation={record['inflation']:5.2f}%, slack={record['slack']:4.1f}%)"
        )
    print(f"  Median DMI: {results['summary_metrics']['dmi_median']:.2f}")
    print(f"  Stress: {results['summary_metrics']['dmi_stress']:.2f}")
    print(
        f"  Income Pressure Gap (Q1-Q5): "
        f"{results['summary_metrics']['dmi_income_pressure_gap']:.2f}"
    )

    print("\n✓ Explicit-period DMI release run completed successfully!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
