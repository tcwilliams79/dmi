#!/usr/bin/env python3
"""
Backfill releases.json from existing DMI release files.
Only includes publicly distributed releases (2025-12 and later).
"""

import sys
import json
from pathlib import Path
from datetime import datetime

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
                    "csv": f"/wp-content/uploads/dmi/dmi-{release_id}.csv",
                    "parquet": f"/wp-content/uploads/dmi/dmi-{release_id}.parquet",
                    "release_note": f"/wp-content/uploads/dmi/releases/{release_id}.html"
                },
                "metrics": {
                    "dmi_median": summary_metrics.get('dmi_median', 0),
                    "dmi_stress": summary_metrics.get('dmi_stress', 0),
                    "income_pressure_gap": summary_metrics.get('dmi_income_pressure_gap', 0),
                    "unemployment": unemployment
                }
            }
            
            releases.append(release)
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
        "schema_version": "1.0.0",
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
        "schema_version": "1.0.0",
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
