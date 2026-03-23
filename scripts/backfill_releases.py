#!/usr/bin/env python3
"""
Backfill releases.json from existing DMI release files.
Only includes publicly distributed releases (2025-12 and later).
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

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


def parse_release_id(filename: str) -> tuple:
    """Parse release_id from filename. Returns (year, month) or None if invalid."""
    # Format: dmi_release_2026-02.json
    try:
        release_id = filename.replace("dmi_release_", "").replace(".json", "")
        year, month = release_id.split('-')
        return (int(year), int(month))
    except:
        return None

def is_public_release(year: int, month: int) -> bool:
    """Check if release is publicly distributed (2025-12 and later)."""
    if year < 2025:
        return False
    if year == 2025 and month < 12:
        return False
    return True

def backfill_releases(output_dir: str = "data/outputs"):
    """Backfill releases.json from existing dmi_release_*.json files (public releases only)."""
    output_path = Path(output_dir)
    
    # Find all dmi_release_*.json files
    release_files = sorted(output_path.glob("dmi_release_*.json"))
    
    if not release_files:
        print("No release files found to backfill")
        return
    
    print(f"Found {len(release_files)} release files, filtering for public releases (2025-12+)")
    
    releases = []
    latest_release = None
    
    # Process each release file
    for release_file in release_files:
        # Extract release_id from filename (e.g., dmi_release_2026-02.json -> 2026-02)
        parsed = parse_release_id(release_file.name)
        if not parsed:
            continue
        
        year, month = parsed
        release_id = f"{year:04d}-{month:02d}"
        
        # Skip non-public releases
        if not is_public_release(year, month):
            print(f"  ⊘ {release_id}: Not in public distribution (pre-2025-12)")
            continue
        
        try:
            with open(release_file, 'r') as f:
                data = json.load(f)
            
            # Extract metrics from the file
            summary_metrics = data.get('summary_metrics', {})
            
            # Convert release_id to data_through_label
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
            month_name = months[month - 1]
            data_through_label = f"{month_name} {year}"
            
            # Get first quintile's slack for unemployment rate
            unemployment = 4.4  # default
            dmi_by_group = data.get('dmi_by_group', [])
            if dmi_by_group:
                unemployment = dmi_by_group[0].get('slack', 4.4)
            
            # Get published_at from metadata if available, otherwise use current date
            metadata = data.get('metadata', {})
            computed_at = metadata.get('computed_at', datetime.now().isoformat())
            # Parse ISO format timestamp and extract date
            try:
                published_at = computed_at.split('T')[0]
            except:
                published_at = datetime.now().strftime('%Y-%m-%d')
            
            # Create release entry
            release = {
                "release_id": release_id,
                "data_through_label": data_through_label,
                "published_at": published_at,
                "status": "superseded",  # Default to superseded, we'll update the latest
                "methodology_version": "v0.1.11",
                "summary": "Full release data available in the accompanying CSV and Parquet files.",
                "urls": {
                    "csv": f"/data/outputs/dmi-{release_id}.csv",
                    "parquet": f"/data/outputs/dmi-{release_id}.parquet",
                    "release_note": f"/data/outputs/releases/{release_id}.html"
                },
                "metrics": {
                    "dmi_median": summary_metrics.get('dmi_median', 0),
                    "dmi_stress": summary_metrics.get('dmi_stress', 0),
                    "income_pressure_gap": summary_metrics.get('dmi_income_pressure_gap', 0),
                    "unemployment": unemployment
                }
            }
            
            releases.append(release)
            
            # Generate summary
            prior_release = releases[-2] if len(releases) > 1 else None
            summary_facts, summary = build_release_summary(release, prior_release)
            release['summary'] = summary
            release['summary_facts'] = summary_facts
            
            latest_release = release  # Keep track of the latest
            
            print(f"  ✓ {release_id}: {data_through_label}")
            
        except Exception as e:
            print(f"  ✗ Error processing {release_id}: {e}")
    
    if not releases:
        print("No public releases found to save")
        return
    
    # Mark the latest as current
    if latest_release:
        latest_release['status'] = 'current'
        current_release_id = latest_release['release_id']
    else:
        current_release_id = releases[0]['release_id']
    
    # Sort in reverse chronological order
    releases.sort(key=lambda x: x['release_id'], reverse=True)
    
    # Build the releases.json structure
    releases_manifest = {
        "schema_version": "1.1.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "current_release_id": current_release_id,
        "releases": releases
    }
    
    # Save releases.json
    releases_path = output_path / "releases.json"
    with open(releases_path, 'w') as f:
        json.dump(releases_manifest, f, indent=2)
    
    print(f"\n✓ Saved {len(releases)} public releases to {releases_path}")
    
    # Build latest.json with only the current release
    latest_manifest = {
        "schema_version": "1.1.0",
        "generated_at": datetime.now().isoformat() + "Z",
        "current_release_id": current_release_id,
        "releases": [latest_release]
    }
    
    latest_path = output_path / "latest.json"
    with open(latest_path, 'w') as f:
        json.dump(latest_manifest, f, indent=2)
    
    print(f"✓ Saved latest release to {latest_path}")

if __name__ == "__main__":
    backfill_releases()
