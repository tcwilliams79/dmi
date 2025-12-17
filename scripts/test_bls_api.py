#!/usr/bin/env python3
"""
Test BLS API client with real CPI and slack data fetch.
"""

import sys
import json
from pathlib import Path

from dmi_pipeline.agents.bls_api_client import (
 fetch_cpi_data,
    fetch_slack_data,
    convert_to_monthly_format,
    pivot_cpi_to_categories,
    save_cpi_data,
    validate_category_coverage
)

def main():
    print("=" * 70)
    print("BLS API Client Test - CPI & Slack Data Fetch")
    print("=" * 70)
    
    # Load series catalog
    catalog_path = Path("registry/series_catalog_v0_1.json")
    with open(catalog_path) as f:
        catalog = json.load(f)
    
    # Extract CPI series IDs (8 major groups)
    cpi_categories = catalog["cpi"]["series_sets"][0]["categories"]
    cpi_series_ids = [cat["series_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    print(f"\n[1/4] Fetching CPI data for 8 major groups...")
    print(f"Categories: {[cat['category_id'] for cat in cpi_categories if cat['category_id'] != 'CPI_ALL_ITEMS']}")
    
    # Fetch CPI data (2023-2024)
    cpi_df = fetch_cpi_data(
        series_ids=cpi_series_ids,
        start_year=2023,
        end_year=2024
    )
    
    # Convert to YYYY-MM format
    cpi_df = convert_to_monthly_format(cpi_df)
    
    # Pivot to wide format
    print(f"\n[2/4] Pivoting CPI data to wide format...")
    cpi_wide = pivot_cpi_to_categories(cpi_df, catalog)
    
    print(f"✓ CPI data shape: {cpi_wide.shape}")
    print(f"  Periods: {cpi_wide['period'].min()} to {cpi_wide['period'].max()}")
    print(f"  Categories: {list(cpi_wide.columns)[1:]}")  # Skip 'period' column
    
    # Sample data
    print(f"\nSample CPI data (first 3 periods):")
    print(cpi_wide.head(3).to_string(index=False))
    
    # Fetch U-3 unemployment data
    print(f"\n[3/4] Fetching U-3 unemployment (slack) data...")
    u3_series_id = catalog["slack"]["national_series"][0]["series_id"]
    
    slack_df = fetch_slack_data(
        series_id=u3_series_id,
        start_year=2023,
        end_year=2024
    )
    
    slack_df = convert_to_monthly_format(slack_df)
    
    print(f"✓ Slack data: {len(slack_df)} observations")
    print(f"  Range: {slack_df['value'].min():.1f}% to {slack_df['value'].max():.1f}%")
    print(f"\nSample slack data (first 5):")
    print(slack_df[['period_yyyymm', 'value']].head(5).to_string(index=False))
    
    # Validate category coverage
    print(f"\n[4/4] Validating category coverage...")
    required_cats = [cat["category_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    validation = validate_category_coverage(
        cpi_df=cpi_wide,
        required_categories=required_cats,
        reference_period="2024-11",
        lookback_months=12
    )
    
    print(f"  Reference period: {validation['reference_period']}")
    print(f"  Lookback period: {validation['lookback_period']}")
    print(f"  Valid: {'✓ YES' if validation['valid'] else '✗ NO'}")
    
    if not validation['valid']:
        print(f"  Missing categories: {validation['missing_categories']}")
        print(f"  Missing periods: {validation['missing_periods']}")
    
    # Save data
    print(f"\nSaving data...")
    save_cpi_data(
        cpi_wide,
        Path("data/staging/cpi_levels_2023_2024.json"),
        metadata={"dataset": "BLS CPI-U", "series_count": len(cpi_series_ids)}
    )
    
    slack_output = Path("data/staging/slack_u3_2023_2024.json")
    slack_output.parent.mkdir(parents=True, exist_ok=True)
    slack_df[['period_yyyymm', 'value']].rename(columns={'period_yyyymm': 'period'}).to_json(
        slack_output, orient='records', indent=2
    )
    print(f"Saved slack data to {slack_output}")
    
    print("\n" + "=" * 70)
    print("✓ BLS API test completed successfully!")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
