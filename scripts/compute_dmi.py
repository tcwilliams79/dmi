#!/usr/bin/env python3
"""
Full DMI Integration - Compute DMI using real data.

Combines:
- Phase 1: Calculator core
- Phase 2: CE weights (2023)
- Phase 3: CPI + slack data (BLS API)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics,
    validate_contributions_sum_to_total
)
from dmi_pipeline.agents.qa_validator import generate_qa_report, print_qa_summary


# Threshold constants for summary generation
THRESHOLDS = {
    'little_changed': 0.05,
    'edged': 0.15,
    'modestly': 0.30,
    'gap_little_changed': 0.015,  # Adjusted to classify 0.0178 as slightly changed
    'gap_slightly': 0.08,
    'unemployment_little_changed': 0.1,
    'unemployment_noticeably': 0.3,
}


def classify_direction(delta: float, thresholds: dict) -> str:
    """Classify direction based on delta and thresholds."""
    abs_delta = abs(delta)
    if abs_delta < thresholds['little_changed']:
        return 'little_changed'
    elif abs_delta < thresholds['edged']:
        return 'edged_up' if delta > 0 else 'edged_down'
    elif abs_delta < thresholds['modestly']:
        return 'rose_modestly' if delta > 0 else 'fell_modestly'
    else:
        return 'rose_sharply' if delta > 0 else 'fell_sharply'


def classify_gap_direction(gap_delta: float) -> str:
    """Classify gap direction."""
    abs_delta = abs(gap_delta)
    if abs_delta < THRESHOLDS['gap_little_changed']:
        return 'gap_little_changed'
    elif abs_delta < THRESHOLDS['gap_slightly']:
        return 'gap_narrowed_slightly' if gap_delta < 0 else 'gap_widened_slightly'
    else:
        return 'gap_narrowed_materially' if gap_delta < 0 else 'gap_widened_materially'


def classify_unemployment_direction(unemp_delta: float) -> str:
    """Classify unemployment direction."""
    abs_delta = abs(unemp_delta)
    if abs_delta < THRESHOLDS['unemployment_little_changed']:
        return 'unemployment_little_changed'
    elif abs_delta < THRESHOLDS['unemployment_noticeably']:
        return 'unemployment_edged_up' if unemp_delta > 0 else 'unemployment_edged_down'
    else:
        return 'unemployment_rose_noticeably' if unemp_delta > 0 else 'unemployment_fell_noticeably'


def build_release_summary(
    current_release: dict,
    prior_release: Optional[dict] = None,
    contributor_context: Optional[dict] = None,
) -> tuple[dict, str]:
    """
    Generate deterministic plain-English summary for a DMI release.
    
    Returns (summary_facts, summary_text)
    """
    metrics = current_release['metrics']
    dmi_median = metrics['dmi_median']
    dmi_stress = metrics['dmi_stress']
    income_pressure_gap = metrics['income_pressure_gap']
    unemployment = metrics['unemployment']
    
    summary_facts = {
        'lower_income_more_pressure': income_pressure_gap > 0,
        'higher_income_more_pressure': income_pressure_gap < 0,
        'pressure_similar_across_bottom_top': abs(income_pressure_gap) < 0.02,
    }
    
    data_through_label = current_release['data_through_label']
    
    # Compute deltas if prior exists
    if prior_release:
        prior_metrics = prior_release['metrics']
        median_delta_mom = dmi_median - prior_metrics['dmi_median']
        stress_delta_mom = dmi_stress - prior_metrics['dmi_stress']
        gap_delta_mom = income_pressure_gap - prior_metrics['income_pressure_gap']
        unemployment_delta_mom = unemployment - prior_metrics['unemployment']
        
        summary_facts.update({
            'median_delta_mom': median_delta_mom,
            'stress_delta_mom': stress_delta_mom,
            'gap_delta_mom': gap_delta_mom,
            'unemployment_delta_mom': unemployment_delta_mom,
            'overall_direction': classify_direction(median_delta_mom, THRESHOLDS),
            'gap_direction': classify_gap_direction(gap_delta_mom),
        })
        
        # Build summary with prior
        sentences = []
        
        # Sentence 1: overall movement
        direction = summary_facts['overall_direction']
        if direction == 'little_changed':
            sentences.append(f"Economic pressure was little changed in {data_through_label}.")
        elif direction == 'edged_up':
            sentences.append(f"Economic pressure edged up in {data_through_label}.")
        elif direction == 'edged_down':
            sentences.append(f"Economic pressure edged down in {data_through_label}.")
        elif direction == 'rose_modestly':
            sentences.append(f"Economic pressure rose modestly in {data_through_label}.")
        elif direction == 'fell_modestly':
            sentences.append(f"Economic pressure fell modestly in {data_through_label}.")
        elif direction == 'rose_sharply':
            sentences.append(f"Economic pressure rose sharply in {data_through_label}.")
        elif direction == 'fell_sharply':
            sentences.append(f"Economic pressure fell sharply in {data_through_label}.")
        
        # Sentence 2: distributional pattern
        if summary_facts['lower_income_more_pressure']:
            if summary_facts['gap_direction'] == 'gap_little_changed':
                sentences.append("Lower-income households continued to face more pressure than higher-income households.")
            elif summary_facts['gap_direction'] == 'gap_narrowed_slightly':
                sentences.append("Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap narrowed slightly from the prior month.")
            elif summary_facts['gap_direction'] == 'gap_widened_slightly':
                sentences.append("Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap widened slightly from the prior month.")
            elif summary_facts['gap_direction'] == 'gap_narrowed_materially':
                sentences.append("Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap narrowed materially from the prior month.")
            elif summary_facts['gap_direction'] == 'gap_widened_materially':
                sentences.append("Lower-income households continued to face more pressure than higher-income households, and the Income Pressure Gap widened materially from the prior month.")
        elif summary_facts['higher_income_more_pressure']:
            sentences.append("Higher-income households faced more pressure than lower-income households.")
        else:
            sentences.append("Pressure was felt more similarly across the bottom and top income fifths.")
        
        # Sentence 3: optional detail
        if contributor_context and 'top_contributors_q1' in contributor_context:
            contributors = contributor_context['top_contributors_q1']
            if len(contributors) == 1:
                sentences.append(f"{contributors[0].title()} remained the largest contributor for the bottom income fifth.")
            elif len(contributors) == 2:
                sentences.append(f"The main contributors for the bottom income fifth were {contributors[0].lower()} and {contributors[1].lower()}.")
            elif len(contributors) >= 3:
                contrib_str = ', '.join(c.lower() for c in contributors[:-1]) + f", and {contributors[-1].lower()}"
                sentences.append(f"For the bottom income fifth, the main contributors remained {contrib_str}.")
        elif prior_release:
            unemp_direction = classify_unemployment_direction(unemployment_delta_mom)
            if unemp_direction != 'unemployment_little_changed':
                if unemp_direction == 'unemployment_edged_up':
                    sentences.append(f"The labor-market backdrop also softened slightly, with unemployment edging up to {unemployment}%.")
                elif unemp_direction == 'unemployment_edged_down':
                    sentences.append(f"The labor-market backdrop improved slightly, with unemployment edging down to {unemployment}%.")
                elif unemp_direction == 'unemployment_rose_noticeably':
                    sentences.append(f"The labor-market backdrop softened noticeably, with unemployment rising to {unemployment}%.")
                elif unemp_direction == 'unemployment_fell_noticeably':
                    sentences.append(f"The labor-market backdrop improved noticeably, with unemployment falling to {unemployment}%.")
        
        summary = ' '.join(sentences)
    else:
        # Fallback: no prior release
        summary_facts.update({
            'overall_direction': 'no_prior',
        })
        summary = f"The {data_through_label} release shows {'higher' if income_pressure_gap > 0 else 'lower' if income_pressure_gap < 0 else 'similar'} measured pressure for lower-income households than for higher-income households. The current dashboard reports a DMI Median of {dmi_median:.2f}, a DMI Stress reading of {dmi_stress:.2f}, and an Income Pressure Gap of {income_pressure_gap:.2f}."
    
    return summary_facts, summary


def load_weights(weights_path: Path) -> pd.DataFrame:
    """Load CE weights from JSON."""
    with open(weights_path) as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['rows'])
    return df


def load_cpi_data(cpi_path: Path) -> pd.DataFrame:
    """Load CPI levels from JSON."""
    with open(cpi_path) as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['data'])
    return df


def load_slack_data(slack_path: Path) -> pd.DataFrame:
    """Load unemployment data from JSON."""
    with open(slack_path) as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    return df


def compute_dmi_for_period(
    cpi_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    slack_df: pd.DataFrame,
    reference_period: str,
    alpha: float = 0.5,
    scale_factor: float = 2.0
) -> dict:
    """
    Compute DMI for a reference period using real data.
    
    Args:
        cpi_df: CPI data with columns [period, CPI_FOOD_BEVERAGES, ...]
        weights_df: Weights with columns [group_id, category_id, weight]
        slack_df: Slack data with columns [period, value]
        reference_period: Period to compute DMI for (YYYY-MM)
        alpha: Inflation vs slack weight (default: 0.5)
        scale_factor: DMI scaling factor (default: 2.0)
    
    Returns:
        Dictionary with DMI results
    """
    print(f"Computing DMI for {reference_period}...")
    
    # Step 1: Compute group-weighted inflation
    print(f"  [1/4] Computing inflation by quintile...")
    inflation_df, contributions_df = compute_group_weighted_inflation(
        cpi_levels=cpi_df,
        weights=weights_df,
        reference_period=reference_period,
        horizon_months=12
    )
    
    print(f"    ✓ Computed inflation for {len(inflation_df)} quintiles")
    for _, row in inflation_df.iterrows():
        print(f"      {row['group_id']}: {row['inflation']:.2f}%")
    
    # Validate contributions
    validate_contributions_sum_to_total(contributions_df, inflation_df)
    print(f"    ✓ Contributions validated (sum to total)")
    
    # Step 2: Extract slack
    print(f"  [2/4] Extracting unemployment rate...")
    slack = compute_slack(
        slack_data=slack_df,
        reference_period=reference_period
    )
    print(f"    ✓ Unemployment (U-3): {slack:.1f}%")
    
    # Step 3: Compute DMI
    print(f"  [3/4] Computing DMI (α={alpha}, scale={scale_factor})...")
    dmi_df = compute_dmi(
        inflation_by_group=inflation_df,
        slack=slack,
        alpha=alpha,
        scale_factor=scale_factor
    )
    
    print(f"    ✓ DMI computed for {len(dmi_df)} quintiles")
    for _, row in dmi_df.iterrows():
        print(f"      {row['group_id']}: DMI={row['dmi']:.2f}")
    
    # Step 4: Summary metrics
    print(f"  [4/4] Computing summary metrics...")
    metrics = compute_summary_metrics(dmi_df)
    
    print(f"    ✓ Summary metrics:")
    print(f"      Median DMI: {metrics['dmi_median']:.2f}")
    print(f"      Stress (max): {metrics['dmi_stress']:.2f}")
    print(f"      Income Pressure Gap (Q1-Q5): {metrics['dmi_income_pressure_gap']:.2f}")
    
    # Compile results
    results = {
        "reference_period": reference_period,
        "parameters": {
            "alpha": alpha,
            "scale_factor": scale_factor,
            "weights_year": 2023
        },
        "dmi_by_group": dmi_df.to_dict(orient='records'),
        "summary_metrics": metrics,
        "inflation_contributions": contributions_df.to_dict(orient='records'),
        "metadata": {
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "num_groups": len(dmi_df),
            "num_categories": len(contributions_df['category_id'].unique())
        }
    }
    
    return results


def save_dmi_output(results: dict, output_path: Path):
    """Save DMI results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Saved DMI output to {output_path}")


def export_csv_parquet(results: dict, reference_period: str):
    """Export DMI results to CSV and Parquet files."""
    dmi_df = pd.DataFrame(results['dmi_by_group'])
    
    # CSV export
    csv_path = Path(f"data/outputs/dmi-{reference_period}.csv")
    dmi_df.to_csv(csv_path, index=False)
    print(f"✓ Saved CSV to {csv_path}")
    
    # Parquet export
    parquet_path = Path(f"data/outputs/dmi-{reference_period}.parquet")
    dmi_df.to_parquet(parquet_path, index=False)
    print(f"✓ Saved Parquet to {parquet_path}")
    
    return csv_path, parquet_path


def generate_release_note_html(
    reference_period: str,
    metrics: dict,
    summary: str = ""
) -> str:
    """Generate HTML release note for the current release."""
    # Parse reference period to human-readable format
    year, month = reference_period.split('-')
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    month_name = months[int(month) - 1]
    data_through = f"{month_name} {year}"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DMI Release {reference_period}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        h1 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }}
        .metrics {{
            background: #f5f7fa;
            border-left: 4px solid #667eea;
            padding: 1rem;
            margin: 1.5rem 0;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
        }}
        .metric-label {{
            font-weight: 600;
        }}
        .metric-value {{
            color: #667eea;
            font-weight: 700;
        }}
        .summary {{
            background: #f9f9f9;
            padding: 1rem;
            border-radius: 4px;
            margin: 1.5rem 0;
        }}
    </style>
</head>
<body>
    <h1>DMI Release: {reference_period}</h1>
    <p><strong>Data Through:</strong> {data_through}</p>
    <p><strong>Published:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
    
    <h2>Key Metrics</h2>
    <div class="metrics">
        <div class="metric-row">
            <span class="metric-label">DMI Median:</span>
            <span class="metric-value">{metrics.get('dmi_median', 0):.2f}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">DMI Stress:</span>
            <span class="metric-value">{metrics.get('dmi_stress', 0):.2f}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Income Pressure Gap:</span>
            <span class="metric-value">{metrics.get('income_pressure_gap', 0):.2f}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Unemployment (U-3):</span>
            <span class="metric-value">{metrics.get('unemployment', 0):.1f}%</span>
        </div>
    </div>
    
    <h2>Summary</h2>
    <div class="summary">
        <p>{summary if summary else 'Full release data available in the accompanying CSV and Parquet files.'}</p>
    </div>
</body>
</html>"""
    
    return html


def save_release_note(html_content: str, reference_period: str):
    """Save release note HTML file."""
    release_dir = Path("data/outputs/releases")
    release_dir.mkdir(parents=True, exist_ok=True)
    
    release_path = release_dir / f"{reference_period}.html"
    with open(release_path, 'w') as f:
        f.write(html_content)
    
    print(f"✓ Saved release note to {release_path}")
    return release_path


def update_releases_json(
    reference_period: str,
    metrics: dict,
    summary: str,
    summary_facts: dict,
    methodology_version: str = "v0.1.11",
    dashboard_url: str = None,
    repo_url: str = None,
    notes: list = None
):
    """Update releases.json with the new release metadata conforming to schema."""
    releases_path = Path("data/outputs/releases.json")
    
    # Load existing releases or create new structure
    releases = []
    if releases_path.exists():
        with open(releases_path, 'r') as f:
            existing = json.load(f)
        
        # Handle both old format (array) and new format (manifest object)
        if isinstance(existing, dict) and 'releases' in existing:
            # Already in new format, get the releases array and filter to new schema only
            for release in existing.get('releases', []):
                # Only keep releases that have the new schema structure AND are not the current release_id
                if 'data_through_label' in release and 'urls' in release:
                    if release.get('release_id') != reference_period:
                        releases.append(release)
        elif isinstance(existing, list):
            # Old format - filter and migrate to new schema
            for release in existing:
                if 'data_through_label' in release and 'urls' in release:
                    if release.get('release_id') != reference_period:
                        releases.append(release)
    
    # Convert reference period to data_through_label format
    year, month = reference_period.split('-')
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    month_name = months[int(month) - 1]
    data_through_label = f"{month_name} {year}"
    
    # Create new release entry
    urls = {
        "csv": f"/data/outputs/dmi-{reference_period}.csv",
        "parquet": f"/data/outputs/dmi-{reference_period}.parquet",
        "release_note": f"/data/outputs/releases/{reference_period}.html"
    }
    if dashboard_url:
        urls["dashboard"] = dashboard_url
    if repo_url:
        urls["repo"] = repo_url
    
    new_release = {
        "release_id": reference_period,
        "data_through_label": data_through_label,
        "published_at": datetime.now().strftime('%Y-%m-%d'),
        "status": "current",
        "methodology_version": methodology_version,
        "summary": summary,
        "summary_facts": summary_facts,
        "urls": urls,
        "metrics": {
            "dmi_median": metrics.get('dmi_median', 0),
            "dmi_stress": metrics.get('dmi_stress', 0),
            "income_pressure_gap": metrics.get('income_pressure_gap', 0),
            "unemployment": metrics.get('unemployment', 0)
        }
    }
    if notes:
        new_release["notes"] = notes
    
    # Mark any other current releases as superseded
    for release in releases:
        if release.get('status') == 'current':
            release['status'] = 'superseded'
    
    # Add new release at top
    releases.insert(0, new_release)
    
    # Build the releases.json structure
    releases_manifest = {
        "schema_version": "1.1.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "current_release_id": reference_period,
        "releases": releases
    }
    
    # Save updated releases.json
    with open(releases_path, 'w') as f:
        json.dump(releases_manifest, f, indent=2)
    
    print(f"✓ Updated releases.json with new release {reference_period}")
    return releases_path


def update_latest_json(
    reference_period: str,
    metrics: dict,
    summary: str,
    summary_facts: dict,
    methodology_version: str = "v0.1.11",
    dashboard_url: str = None,
    repo_url: str = None,
    notes: list = None
):
    """Update latest.json with the most recent release metadata conforming to schema."""
    latest_path = Path("data/outputs/latest.json")
    
    # Convert reference period to data_through_label format
    year, month = reference_period.split('-')
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    month_name = months[int(month) - 1]
    data_through_label = f"{month_name} {year}"
    
    urls = {
        "csv": f"/data/outputs/dmi-{reference_period}.csv",
        "parquet": f"/data/outputs/dmi-{reference_period}.parquet",
        "release_note": f"/data/outputs/releases/{reference_period}.html"
    }
    if dashboard_url:
        urls["dashboard"] = dashboard_url
    if repo_url:
        urls["repo"] = repo_url
    
    latest_release = {
        "release_id": reference_period,
        "data_through_label": data_through_label,
        "published_at": datetime.now().strftime('%Y-%m-%d'),
        "status": "current",
        "methodology_version": methodology_version,
        "summary": summary,
        "summary_facts": summary_facts,
        "urls": urls,
        "metrics": {
            "dmi_median": metrics.get('dmi_median', 0),
            "dmi_stress": metrics.get('dmi_stress', 0),
            "income_pressure_gap": metrics.get('income_pressure_gap', 0),
            "unemployment": metrics.get('unemployment', 0)
        }
    }
    if notes:
        latest_release["notes"] = notes
    
    # Build the latest.json structure following the same schema as releases.json
    latest_manifest = {
        "schema_version": "1.1.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "current_release_id": reference_period,
        "releases": [latest_release]
    }
    
    with open(latest_path, 'w') as f:
        json.dump(latest_manifest, f, indent=2)
    
    print(f"✓ Updated latest.json with release {reference_period}")
    return latest_path


def main():
    print("=" * 80)
    print("DMI v0.1.8 - Full Integration Test")
    print("=" * 80)
    
    # Determine the year range for data files based on current date
    # Data files span Oct-Nov of year N to Sep-Oct of year N+1
    # e.g., cpi_levels_2024_2025.json covers late 2024 through most of 2025
    now = datetime.now()
    # If we're in the later months (Nov-Dec), we need the current_year to next_year file
    if now.month >= 11:
        start_year = now.year
        end_year = now.year + 1
    else:
        start_year = now.year - 1
        end_year = now.year
    
    # Paths
    weights_path = Path("data/curated/weights_by_group_2023.json")
    cpi_path = Path(f"data/staging/cpi_levels_{start_year}_{end_year}.json")
    slack_path = Path(f"data/staging/slack_u3_{start_year}_{end_year}.json")
    
    # Load data
    print("\nLoading data...")
    weights_df = load_weights(weights_path)
    print(f"  ✓ Weights: {len(weights_df)} records (5 quintiles × 8 categories)")
    
    cpi_df = load_cpi_data(cpi_path)
    print(f"  ✓ CPI data: {len(cpi_df)} periods, 8 categories")
    
    slack_df = load_slack_data(slack_path)
    print(f"  ✓ Slack data: {len(slack_df)} periods")
    
    # Determine reference period dynamically from CPI data
    # Use the most recent complete month available in the data
    print("\n" + "=" * 80)
    available_periods = sorted(cpi_df['period'].unique())
    reference_period = available_periods[-1]  # Latest available period
    print(f"Using reference period: {reference_period} (latest in data)")
    
    results = compute_dmi_for_period(
        cpi_df=cpi_df,
        weights_df=weights_df,
        slack_df=slack_df,
        reference_period=reference_period,
        alpha=0.5,
        scale_factor=2.0
    )
    
    # Save results
    output_path = Path(f"data/outputs/dmi_release_{reference_period}.json")
    save_dmi_output(results, output_path)
    
    # Generate QA report
    print("\n" + "=" * 80)
    print("Generating QA Report...")
    print("=" * 80)
    
    qa_report = generate_qa_report(
        dmi_output=results,
        cpi_data=cpi_df,
        weights_data=weights_df,
        slack_data=slack_df,
        output_path=Path(f"data/outputs/qa_report_{reference_period}.json")
    )
    
    print_qa_summary(qa_report)
    
    # Create CSV and Parquet files
    print("\n" + "=" * 80)
    print("Creating CSV and Parquet files...")
    print("=" * 80)
    
    csv_path, parquet_path = export_csv_parquet(results, reference_period)
    
    # Generate release note HTML
    print("\n" + "=" * 80)
    print("Generating release note HTML...")
    print("=" * 80)
    
    # Generate summary
    current_release = {
        'release_id': reference_period,
        'data_through_label': f"{['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][int(reference_period.split('-')[1]) - 1]} {reference_period.split('-')[0]}",
        'metrics': {
            'dmi_median': results['summary_metrics']['dmi_median'],
            'dmi_stress': results['summary_metrics']['dmi_stress'],
            'income_pressure_gap': results['summary_metrics']['dmi_income_pressure_gap'],
            'unemployment': results['dmi_by_group'][0]['slack']
        }
    }
    
    # Get prior release
    prior_release = None
    releases_path = Path("data/outputs/releases.json")
    if releases_path.exists():
        with open(releases_path, 'r') as f:
            existing = json.load(f)
        if isinstance(existing, dict) and 'releases' in existing:
            existing_releases = existing.get('releases', [])
        elif isinstance(existing, list):
            existing_releases = existing
        else:
            existing_releases = []
        if existing_releases:
            # Sort by release_id descending, take the first (latest)
            existing_releases.sort(key=lambda x: x['release_id'], reverse=True)
            prior_release = existing_releases[0]
    
    summary_facts, summary = build_release_summary(current_release, prior_release)
    
    release_html = generate_release_note_html(
        reference_period=reference_period,
        metrics={
            'dmi_median': results['summary_metrics']['dmi_median'],
            'dmi_stress': results['summary_metrics']['dmi_stress'],
            'income_pressure_gap': results['summary_metrics']['dmi_income_pressure_gap'],
            'unemployment': results['dmi_by_group'][0]['slack']  # U-3 rate from Q1
        },
        summary=summary
    )
    save_release_note(release_html, reference_period)
    
    # Update releases.json
    print("\n" + "=" * 80)
    print("Updating releases.json and latest.json...")
    print("=" * 80)
    
    update_releases_json(
        reference_period=reference_period,
        metrics={
            'dmi_median': results['summary_metrics']['dmi_median'],
            'dmi_stress': results['summary_metrics']['dmi_stress'],
            'income_pressure_gap': results['summary_metrics']['dmi_income_pressure_gap'],
            'unemployment': results['dmi_by_group'][0]['slack']
        },
        summary=summary,
        summary_facts=summary_facts
    )
    
    # Update latest.json
    update_latest_json(
        reference_period=reference_period,
        metrics={
            'dmi_median': results['summary_metrics']['dmi_median'],
            'dmi_stress': results['summary_metrics']['dmi_stress'],
            'income_pressure_gap': results['summary_metrics']['dmi_income_pressure_gap'],
            'unemployment': results['dmi_by_group'][0]['slack']
        },
        summary=summary,
        summary_facts=summary_facts
    )
    
    # Print summary
    print("\n" + "=" * 80)
    print("DMI SUMMARY")
    print("=" * 80)
    print(f"Period: {reference_period}")
    print(f"Weights Year: 2023")
    print(f"\nDMI by Income Quintile:")
    for record in results['dmi_by_group']:
        print(f"  {record['group_id']}: DMI={record['dmi']:6.2f}  (inflation={record['inflation']:5.2f}%, slack={record['slack']:4.1f}%)")
    
    print(f"\nSummary Metrics:")
    print(f"  Median DMI: {results['summary_metrics']['dmi_median']:.2f}")
    print(f"  Stress (Q1): {results['summary_metrics']['dmi_stress']:.2f}")
    print(f"  Income Pressure Gap (Q1-Q5): {results['summary_metrics']['dmi_income_pressure_gap']:.2f}")
    
    print("\n" + "=" * 80)
    print("✓ Full DMI integration test completed successfully!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
