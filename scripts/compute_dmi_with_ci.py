#!/usr/bin/env python3
"""
Compute DMI with Confidence Intervals

Generates DMI estimates with bootstrap confidence intervals
for specified period, quantifying uncertainty from CE weights sampling error.

Usage:
    ./venv/bin/python -m scripts.compute_dmi_with_ci [--period YYYY-MM] [--bootstrap N]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd

from dmi_calculator.uncertainty import compute_dmi_with_confidence_intervals
from dmi_pipeline.agents.bls_api_client import (
    fetch_cpi_data,
    fetch_slack_data,
    convert_to_monthly_format,
    pivot_cpi_to_categories
)


def main():
    parser = argparse.ArgumentParser(description='Compute DMI with confidence intervals')
    parser.add_argument('--period', default='2024-11', help='Reference period (YYYY-MM)')
    parser.add_argument('--bootstrap', type=int, default=1000, help='Number of bootstrap iterations')
    parser.add_argument('--weight-cv', type=float, default=0.05, help='Assumed CV for CE weights')
    args = parser.parse_args()
    
    print("=" * 80)
    print("DMI with Bootstrap Confidence Intervals")
    print("=" * 80)
    
    # Configuration
    reference_period = args.period
    n_bootstrap = args.bootstrap
    weight_cv = args.weight_cv
    data_dir = Path("data")
    registry_dir = Path("registry")
    
    # Load catalog
    catalog_path = registry_dir / "series_catalog_v0_1.json"
    with open(catalog_path) as f:
        catalog = json.load(f)
    
    # Load CE weights
    weights_path = data_dir / "curated" / "weights_by_group_2023.json"
    with open(weights_path) as f:
        data = json.load(f)
    weights_df = pd.DataFrame(data['rows'])
    print(f"\n✓ Loaded CE weights: {len(weights_df)} records")
    
    # Fetch CPI data
    print(f"\n📊 Fetching CPI data for {reference_period}...")
    cpi_categories = catalog["cpi"]["series_sets"][0]["categories"]
    cpi_series_ids = [cat["series_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    ref_year = int(reference_period[:4])
    cpi_df = fetch_cpi_data(cpi_series_ids, ref_year - 1, ref_year)
    cpi_df = convert_to_monthly_format(cpi_df)
    cpi_wide = pivot_cpi_to_categories(cpi_df, catalog)
    print(f"✓ CPI data loaded: {len(cpi_wide)} periods")
    
    # Fetch U-3 unemployment
    print(f"\n📈 Fetching U-3 unemployment data...")
    u3_series_id = catalog["slack"]["national_series"][0]["series_id"]
    slack_df = fetch_slack_data(u3_series_id, ref_year - 1, ref_year)
    slack_df = convert_to_monthly_format(slack_df)
    slack_df = slack_df[['period_yyyymm', 'value']].rename(columns={'period_yyyymm': 'period'})
    print(f"✓ U-3 data loaded: {len(slack_df)} periods")
    
    # Compute DMI with confidence intervals
    results = compute_dmi_with_confidence_intervals(
        cpi_df=cpi_wide,
        weights_df=weights_df,
        slack_df=slack_df,
        reference_period=reference_period,
        n_bootstrap=n_bootstrap,
        weight_cv=weight_cv,
        random_seed=42
    )
    
    # Save results
    output_dir = data_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"dmi_release_{reference_period}_with_ci.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    print(f"\n" + "=" * 80)
    print("✓ DMI with confidence intervals complete!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
