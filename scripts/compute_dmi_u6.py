#!/usr/bin/env python3
"""
DMI Alternative Specification: U-6 Unemployment

Computes DMI using U-6 (unemployment + underemployment + marginally attached)
instead of U-3 (standard unemployment rate).

U-6 provides a broader measure of labor market slack, including:
- Unemployed workers actively seeking work (U-3)
- Discouraged workers
- Marginally attached to labor force
- Part-time workers for economic reasons

Expected: U-6 DMI values ~3-4 points higher than U-3 DMI
"""

import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics
)
from dmi_pipeline.agents.bls_api_client import (
    fetch_slack_data,
    fetch_cpi_data,
    convert_to_monthly_format,
    pivot_cpi_to_categories
)


def main():
    print("=" * 80)
    print("DMI Alternative Specification: U-6 Unemployment")
    print("=" * 80)
    
    # Configuration
    reference_period = "2024-11"  # Can be changed or passed as argument
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
    
    # Fetch CPI data (same as baseline)
    print(f"\n📊 Fetching CPI data for {reference_period}...")
    cpi_categories = catalog["cpi"]["series_sets"][0]["categories"]
    cpi_series_ids = [cat["series_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    ref_year = int(reference_period[:4])
    cpi_df = fetch_cpi_data(cpi_series_ids, ref_year - 1, ref_year)
    cpi_df = convert_to_monthly_format(cpi_df)
    cpi_wide = pivot_cpi_to_categories(cpi_df, catalog)
    print(f"✓ CPI data loaded: {len(cpi_wide)} periods")
    
    # Fetch U-6 unemployment (ALTERNATIVE)
    print(f"\n📈 Fetching U-6 unemployment data...")
    u6_series = [s for s in catalog["slack"]["national_series"] if s["metric"] == "U6"][0]
    u6_series_id = u6_series["series_id"]
    print(f"  Series: {u6_series_id} - {u6_series['label']}")
    
    slack_df = fetch_slack_data(u6_series_id, ref_year - 1, ref_year)
    slack_df = convert_to_monthly_format(slack_df)
    slack_df = slack_df[['period_yyyymm', 'value']].rename(columns={'period_yyyymm': 'period'})
    print(f"✓ U-6 data loaded: {len(slack_df)} periods")
    
    # Compute inflation (same as baseline)
    print(f"\n🧮 Computing inflation by quintile...")
    inflation_df, contributions_df = compute_group_weighted_inflation(
        cpi_levels=cpi_wide,
        weights=weights_df,
        reference_period=reference_period,
        horizon_months=12
    )
    
    for _, row in inflation_df.iterrows():
        print(f"  {row['group_id']}: {row['inflation']:.2f}%")
    
    # Extract U-6 slack (ALTERNATIVE)
    print(f"\n📉 Extracting U-6 unemployment rate...")
    slack_u6 = compute_slack(slack_data=slack_df, reference_period=reference_period)
    print(f"  U-6 Rate: {slack_u6:.1f}%")
    
    # Compute DMI with U-6
    print(f"\n💡 Computing DMI with U-6...")
    dmi_df = compute_dmi(
        inflation_by_group=inflation_df,
        slack=slack_u6,
        alpha=0.5,
        scale_factor=2.0
    )
    
    print(f"\n  DMI by Income Quintile (U-6):")
    for _, row in dmi_df.iterrows():
        print(f"    {row['group_id']}: DMI={row['dmi']:6.2f}  (inflation={row['inflation']:5.2f}%, U-6={row['slack']:4.1f}%)")
    
    # Summary metrics
    metrics = compute_summary_metrics(dmi_df)
    
    # Compile results
    results = {
        "reference_period": reference_period,
        "specification": "U6_UNEMPLOYMENT",
        "description": "DMI computed using U-6 unemployment rate (broader labor market slack measure)",
        "parameters": {
            "alpha": 0.5,
            "scale_factor": 2.0,
            "weights_year": 2023,
            "slack_measure": "U6",
            "slack_series_id": u6_series_id
        },
        "dmi_by_group": dmi_df.to_dict(orient='records'),
        "summary_metrics": metrics,
        "inflation_contributions": contributions_df.to_dict(orient='records'),
        "metadata": {
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "num_groups": len(dmi_df),
            "note": "U-6 includes unemployed + underemployed + marginally attached workers"
        }
    }
    
    # Save results
    output_dir = data_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"dmi_release_{reference_period}_u6.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    # Generate comparison report
    print(f"\n" + "=" * 80)
    print("COMPARISON: U-6 vs U-3 (Baseline)")
    print("=" * 80)
    
    # Load baseline U-3 results if available
    baseline_file = output_dir / f"dmi_release_{reference_period}.json"
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline = json.load(f)
        
        baseline_slack = baseline['dmi_by_group'][0]['slack']
        u6_u3_diff = slack_u6 - baseline_slack
        
        print(f"\nLabor Market Slack:")
        print(f"  U-3 (baseline): {baseline_slack:.1f}%")
        print(f"  U-6 (alternative): {slack_u6:.1f}%")
        print(f"  Difference: +{u6_u3_diff:.1f} percentage points")
        
        print(f"\nDMI Comparison:")
        print(f"  {'Quintile':<10} {'U-3 DMI':<12} {'U-6 DMI':<12} {'Difference'}")
        print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*10}")
        
        for i, u6_row in enumerate(results['dmi_by_group']):
            baseline_row = baseline['dmi_by_group'][i]
            diff = u6_row['dmi'] - baseline_row['dmi']
            print(f"  {u6_row['group_id']:<10} {baseline_row['dmi']:>11.2f}  {u6_row['dmi']:>11.2f}  {diff:>+9.2f}")
        
        avg_diff = sum(u6_row['dmi'] - baseline['dmi_by_group'][i]['dmi'] 
                      for i, u6_row in enumerate(results['dmi_by_group'])) / len(results['dmi_by_group'])
        
        print(f"\n  Average DMI increase with U-6: +{avg_diff:.2f} points")
        print(f"\n💡 Interpretation:")
        print(f"  U-6 DMI is consistently higher, reflecting broader labor market slack.")
        print(f"  Use U-6 when analyzing periods with high underemployment or")
        print(f"  discouraged workers (e.g., Great Recession, COVID-19).")
    else:
        print(f"\n⚠️  Baseline U-3 results not found at: {baseline_file}")
        print(f"  Run compute_dmi.py first to generate comparison.")
    
    print(f"\n" + "=" * 80)
    print("✓ U-6 alternative specification complete!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
