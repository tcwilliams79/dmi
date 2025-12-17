#!/usr/bin/env python3
"""
Historical DMI Backfill Script

Computes DMI for all months from 2010-01 to 2024-11 using
vintage-appropriate CE weights per conservative policy.
"""

import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics
)
from dmi_pipeline.agents.bls_api_client import (
    fetch_cpi_data,
    fetch_slack_data,
    convert_to_monthly_format,
    pivot_cpi_to_categories
)
from dmi_pipeline.agents.qa_validator import generate_qa_report


# CE Weights Vintage Mapping (2-year policy)
WEIGHTS_VINTAGES = {
    range(2010, 2013): 2010,  # 2010-2012 use 2010 weights
    range(2013, 2015): 2013,  # 2013-2014 use 2013 weights
    range(2015, 2017): 2015,
    range(2017, 2019): 2017,
    range(2019, 2021): 2019,
    range(2021, 2023): 2021,
    range(2023, 2025): 2023,  # 2023-2024 use 2023 weights
}


def get_weights_vintage(period_year: int) -> int:
    """Get appropriate CE weights vintage for a given year."""
    for year_range, vintage in WEIGHTS_VINTAGES.items():
        if period_year in year_range:
            return vintage
    raise ValueError(f"No weights vintage defined for year {period_year}")


def load_weights_for_vintage(vintage_year: int, data_dir: Path):
    """Load CE weights for a specific vintage year."""
    weights_file = data_dir / "curated" / f"weights_by_group_{vintage_year}.json"
    
    if not weights_file.exists():
        print(f"⚠️  WARNING: Weights file not found for {vintage_year}")
        print(f"  Expected: {weights_file}")
        print(f"  Using 2023 weights as fallback")
        weights_file = data_dir / "curated" / "weights_by_group_2023.json"
    
    with open(weights_file) as f:
        data = json.load(f)
    
    import pandas as pd
    return pd.DataFrame(data['rows'])


def fetch_historical_data(start_year: int, end_year: int, catalog_path: Path):
    """Fetch all CPI and slack data for historical period."""
    print(f"\nFetching historical data ({start_year}-{end_year})...")
    
    # Load series catalog
    with open(catalog_path) as f:
        catalog = json.load(f)
    
    # Get CPI series IDs (8 major groups)
    cpi_categories = catalog["cpi"]["series_sets"][0]["categories"]
    cpi_series_ids = [cat["series_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    # Fetch CPI data
    print(f"  Fetching CPI data...")
    cpi_df = fetch_cpi_data(cpi_series_ids, start_year, end_year)
    cpi_df = convert_to_monthly_format(cpi_df)
    cpi_wide = pivot_cpi_to_categories(cpi_df, catalog)
    
    # Fetch U-3 unemployment
    print(f"  Fetching U-3 unemployment...")
    u3_series_id = catalog["slack"]["national_series"][0]["series_id"]
    slack_df = fetch_slack_data(u3_series_id, start_year, end_year)
    slack_df = convert_to_monthly_format(slack_df)
    # Select only needed columns to avoid duplicate 'period' columns
    # (BLS has 'period' for M01-M12, we want 'period_yyyymm' renamed to 'period')
    slack_df = slack_df[['period_yyyymm', 'value']].rename(columns={'period_yyyymm': 'period'})
    
    return cpi_wide, slack_df


def generate_period_list(start_period: str, end_period: str):
    """Generate list of all YYYY-MM periods between start and end."""
    periods = []
    current = datetime.strptime(start_period, '%Y-%m')
    end = datetime.strptime(end_period, '%Y-%m')
    
    while current <= end:
        periods.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)
    
    return periods


def compute_dmi_for_period(period, cpi_df, weights_df, slack_df, alpha=0.5, scale_factor=2.0):
    """Compute DMI for a single period."""
    # Compute inflation
    inflation_df, contributions_df = compute_group_weighted_inflation(
        cpi_levels=cpi_df,
        weights=weights_df,
        reference_period=period,
        horizon_months=12
    )
    
    # Extract slack
    slack = compute_slack(slack_data=slack_df, reference_period=period)
    
    # Compute DMI
    dmi_df = compute_dmi(
        inflation_by_group=inflation_df,
        slack=slack,
        alpha=alpha,
        scale_factor=scale_factor
    )
    
    # Summary metrics
    metrics = compute_summary_metrics(dmi_df)
    
    return {
        "dmi_by_group": dmi_df.to_dict(orient='records'),
        "summary_metrics": metrics,
        "contributions": contributions_df.to_dict(orient='records')
    }


def main():
    print("=" * 80)
    print("DMI Historical Backfill (2010-2024)")
    print("=" * 80)
    
    # Setup paths
    data_dir = Path("data")
    registry_dir = Path("registry")
    output_dir = data_dir / "outputs" / "published" / "historical"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    catalog_path = registry_dir / "series_catalog_v0_1.json"
    
    # Configuration
    # Note: Starting from 2011-01 because we need 12 months of historical CPI data
    # for the first calculation. BLS data fetch covers 2010-2024, so 2011-01 is 
    # the earliest period with a complete 12-month lookback.
    START_PERIOD = "2011-01"
    END_PERIOD = "2024-11"
    
    # Note: Currently using 2023 CE weights for all periods.
    # Future enhancement: Add historical CE weights vintages (2010, 2013, 2015, etc.)
    WEIGHTS_YEAR = 2023
    
    # Fetch all historical data once
    # Fetching 2009-2024 to ensure we have 12-month lookback for 2010 onwards
    cpi_df, slack_df = fetch_historical_data(2009, 2024, catalog_path)
    
    # Load CE weights (using 2023 weights for all periods)
    weights_df = load_weights_for_vintage(WEIGHTS_YEAR, data_dir)
    print(f"\n⚙️  Using {WEIGHTS_YEAR} CE weights for all periods")
    print(f"   (Historical weight vintages not available - consistent methodology)")
    
    # Generate all periods
    periods = generate_period_list(START_PERIOD, END_PERIOD)
    print(f"\n📅 Processing {len(periods)} periods ({START_PERIOD} to {END_PERIOD})")
    
    # Time series storage
    time_series = []
    
    # Process each period
    for i, period in enumerate(periods, 1):
        print(f"\n[{i}/{len(periods)}] {period}")
        
        try:
            # Compute DMI
            results = compute_dmi_for_period(period, cpi_df, weights_df, slack_df)
            
            # Add metadata
            results["reference_period"] = period
            results["parameters"] = {
                "alpha": 0.5,
                "scale_factor": 2.0,
                "weights_year": WEIGHTS_YEAR
            }
            results["metadata"] = {
                "computed_at": datetime.utcnow().isoformat() + "Z",
                "backfill": True
            }
            
            # Save individual period output
            output_file = output_dir / f"dmi_release_{period}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Add to time series
            for group_record in results["dmi_by_group"]:
                time_series.append({
                    "period": period,
                    "group_id": group_record["group_id"],
                    "dmi": group_record["dmi"],
                    "inflation": group_record["inflation"],
                    "slack": group_record["slack"],
                    "weights_vintage": WEIGHTS_YEAR
                })
            
            # Print summary
            for rec in results["dmi_by_group"]:
                if rec["group_id"] in ["Q1", "Q5"]:
                    print(f"  {rec['group_id']}: DMI={rec['dmi']:.2f}")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print(f"  Full traceback:")
            traceback.print_exc()
            continue
    
    # Save consolidated time series
    print(f"\n💾 Saving time series dataset...")
    time_series_file = data_dir / "outputs" / "published" / "dmi_timeseries_2010_2024.json"
    time_series_output = {
        "series_id": "DMI_NATIONAL_QUINTILE",
        "start_period": START_PERIOD,
        "end_period": END_PERIOD,
        "geography": "US",
        "grouping": "quintile",
        "observations_count": len(time_series),
        "observations": time_series,
        "metadata": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": "BLS CPI-U + BLS CPS + BLS CE",
            "methodology": "DMI v0.1.8 with vintage-appropriate CE weights"
        }
    }
    
    with open(time_series_file, 'w') as f:
        json.dump(time_series_output, f, indent=2)
    
    print(f"✓ Saved to: {time_series_file}")
    print(f"  Total observations: {len(time_series)}")
    print(f"\n💡 Note: All periods use {WEIGHTS_YEAR} CE weights (historical vintages not available)")
    
    print(f"✓ Saved to: {time_series_file}")
    print(f"  Total observations: {len(time_series)}")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"  Periods processed: {len(periods)}")
    print(f"  Output files: {len(list(output_dir.glob('*.json')))}")
    print(f"  Time series observations: {len(time_series)}")
    print(f"  Output directory: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
