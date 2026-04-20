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
import pandas as pd
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
    parser.add_argument(
    "--spec",
    choices=["baseline", "slack_plus", "core"],
    default="baseline",
    help="Which DMI specification to compute."
    )
    return parser.parse_args()

def output_suffix_for_spec(spec: str) -> str:
    return "" if spec == "baseline" else f"_{spec}"


def build_core_weights(weights_df: pd.DataFrame) -> pd.DataFrame:
    core_weights = weights_df[weights_df["category_id"] != "CPI_FOOD_BEVERAGES"].copy()

    for group_id in core_weights["group_id"].unique():
        mask = core_weights["group_id"] == group_id
        total = core_weights.loc[mask, "weight"].sum()
        core_weights.loc[mask, "weight"] = core_weights.loc[mask, "weight"] / total

    return core_weights


def load_slack_for_spec(reference_period: str, spec: str, start_year: int, end_year: int) -> pd.DataFrame:
    # baseline/core: use staged U-3
    if spec in ("baseline", "core"):
        slack_path = Path(f"data/staging/slack_u3_{start_year}_{end_year}.json")
        if not slack_path.exists():
            raise SystemExit(f"Missing staged U-3 slack file: {slack_path}")
        return load_slack_data(slack_path)

    # slack_plus: prefer staged U-6 if available; otherwise fetch and cache
    slack_u6_path = Path(f"data/staging/slack_u6_{start_year}_{end_year}.json")
    if slack_u6_path.exists():
        return load_slack_data(slack_u6_path)

    from dmi_pipeline.agents.bls_api_client import fetch_slack_data, convert_to_monthly_format
    catalog_path = Path("registry/series_catalog_v0_1.json")
    with open(catalog_path) as f:
        catalog = json.load(f)

    u6_series = [s for s in catalog["slack"]["national_series"] if s["metric"] == "U6"][0]
    slack_df = fetch_slack_data(u6_series["series_id"], start_year, end_year)
    slack_df = convert_to_monthly_format(slack_df)
    slack_df = slack_df[["period_yyyymm", "value"]].rename(columns={"period_yyyymm": "period"})

    # cache for reproducibility
    slack_u6_path.parent.mkdir(parents=True, exist_ok=True)
    with open(slack_u6_path, "w") as f:
        json.dump(slack_df.to_dict(orient="records"), f, indent=2)

    return slack_df


def spec_description(spec: str) -> str:
    return {
        "baseline": "Headline DMI using current inflation inputs and U-3 unemployment.",
        "slack_plus": "Companion DMI using broader labor-market slack.",
        "core": "Companion DMI using core inflation inputs."
    }[spec]


def main(spec: str="baseline", weights_year: str="2023") -> int:
    args = parse_args()
    reference_period = args.reference_period
    spec = args.spec
    suffix = output_suffix_for_spec(spec)

    print("=" * 80)
    print("DMI Release Runner")
    print("=" * 80)
    print(f"Requested reference period: {reference_period}")

    start_year, end_year = staging_window_for_period(reference_period)

    weights_path = Path("data/curated/weights_by_group_2023.json")
    cpi_path = Path(f"data/staging/cpi_levels_{start_year}_{end_year}.json")
    
    if spec == "slack_plus": 
        slack_measure = "u6"
    else:
        slack_measure = "u3" 
    
    slack_path = Path(f"data/staging/slack_{slack_measure}_{start_year}_{end_year}.json")

    if not cpi_path.exists():
        raise SystemExit(f"Missing staged CPI file for {reference_period}: {cpi_path}")

    print("\nLoading data...")
    weights_df = load_weights(weights_path)
    print(f"  ✓ Weights: {len(weights_df)} records")

    cpi_df = load_cpi_data(cpi_path)
    print(f"  ✓ CPI data: {len(cpi_df)} periods from {cpi_path.name}")

    # NEW: load slack according to spec (U3 baseline/core, U6 for slack_plus)
    slack_df = load_slack_for_spec(reference_period, spec, start_year, end_year)   
    print(f"  ✓ Slack data: {len(slack_df)} periods from {slack_path.name}")

    ensure_period_available(reference_period, cpi_df, slack_df)

    print("\n" + "=" * 80)
    print(f"Computing release for explicit period {reference_period}")
    print(f"Spec is {spec})
    results = compute_dmi_for_period(
        cpi_df=cpi_df,
        weights_df=weights_df,
        slack_df=slack_df,
        reference_period=reference_period,
        alpha=0.5,
        scale_factor=2.0,
        spec=spec
    )

    # Add spec metadata
    results["specification"] = spec
    results["description"] = spec_description(spec)
    results["parameters"]["spec_id"] = spec
    results["parameters"]["slack_measure"] = slack_measure  #  slack_measure is set earlier based on the spec type
    
    if spec == "core":
        results["parameters"]["inflation_measure"] = "CORE_CPI"
        results["parameters"]["excluded_categories"] = ["CPI_FOOD_BEVERAGES"]
    else:
        results["parameters"]["inflation_measure"] = "HEADLINE_CPI"
        
    # NEW: write outputs with suffix so specs don't overwrite each other
    suffix = output_suffix_for_spec(spec)
    output_path = Path(f"data/outputs/dmi_release_{reference_period}{suffix}.json")
    save_dmi_output(results, output_path)

    print("\n" + "=" * 80)
    print("Generating QA Report...")
    print("=" * 80)
    qa_report = generate_qa_report(
        dmi_output=results,
        cpi_data=cpi_df,
        weights_data=weights_df,
        slack_data=slack_df,
        output_path=Path(f"data/outputs/qa_report_{reference_period}_{spec}.json"),
    )
    print_qa_summary(qa_report, spec)

    print("\n" + "=" * 80)
    print("Creating CSV and Parquet files...")
    print("=" * 80)
    export_csv_parquet(results, reference_period, spec)

    # only baseline gets release note + manifests + health + timeseries
    if spec == "baseline":
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
    else:
        print(f"Saved companion specification: {spec} -> {output_path}")
        
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
