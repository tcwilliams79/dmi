#!/usr/bin/env python3
"""
DMI Alternative Specification: Core CPI

Computes DMI using Core CPI (excluding food and beverages) to measure
inflation sensitivity to volatile categories.

Core CPI excludes:
- Food and beverages (high volatility, large share for lower incomes)

This alternative helps assess whether DMI differences across quintiles
are driven by volatile food prices or more persistent inflation.

Expected: Core DMI should be similar to headline DMI (±0.5 points),
but lower-income quintiles may show larger differences due to higher
food budget shares.
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
    print("DMI Alternative Specification: Core CPI (Excluding Food)")
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
    
    # Filter out food categories (CORE CPI - ALTERNATIVE)
    print(f"\n🔍 Creating Core CPI weights (excluding food and beverages)...")
    core_weights = weights_df[weights_df['category_id'] != 'CPI_FOOD_BEVERAGES'].copy()
    print(f"  Excluded: CPI_FOOD_BEVERAGES")
    print(f"  Remaining categories: {core_weights['category_id'].nunique()}")
    
    # Renormalize weights to sum to 1.0 for each group
    print(f"\n⚖️  Renormalizing weights...")
    for group_id in core_weights['group_id'].unique():
        group_mask = core_weights['group_id'] == group_id
        weight_sum = core_weights.loc[group_mask, 'weight'].sum()
        core_weights.loc[group_mask, 'weight'] = core_weights.loc[group_mask, 'weight'] / weight_sum
        
        # Verify
        new_sum = core_weights.loc[group_mask, 'weight'].sum()
        print(f"  {group_id}: {weight_sum:.4f} → {new_sum:.4f}")
    
    # Fetch CPI data (same as baseline)
    print(f"\n📊 Fetching CPI data for {reference_period}...")
    cpi_categories = catalog["cpi"]["series_sets"][0]["categories"]
    cpi_series_ids = [cat["series_id"] for cat in cpi_categories if cat["category_id"] != "CPI_ALL_ITEMS"]
    
    ref_year = int(reference_period[:4])
    cpi_df = fetch_cpi_data(cpi_series_ids, ref_year - 1, ref_year)
    cpi_df = convert_to_monthly_format(cpi_df)
    cpi_wide = pivot_cpi_to_categories(cpi_df, catalog)
    print(f"✓ CPI data loaded: {len(cpi_wide)} periods")
    
    # Fetch U-3 unemployment (same as baseline)
    print(f"\n📈 Fetching U-3 unemployment data...")
    u3_series_id = catalog["slack"]["national_series"][0]["series_id"]
    slack_df = fetch_slack_data(u3_series_id, ref_year - 1, ref_year)
    slack_df = convert_to_monthly_format(slack_df)
    slack_df = slack_df[['period_yyyymm', 'value']].rename(columns={'period_yyyymm': 'period'})
    print(f"✓ U-3 data loaded: {len(slack_df)} periods")
    
    # Compute core inflation (ALTERNATIVE - using filtered weights)
    print(f"\n🧮 Computing CORE inflation by quintile (excluding food)...")
    inflation_df, contributions_df = compute_group_weighted_inflation(
        cpi_levels=cpi_wide,
        weights=core_weights,  # USING CORE WEIGHTS
        reference_period=reference_period,
        horizon_months=12
    )
    
    for _, row in inflation_df.iterrows():
        print(f"  {row['group_id']}: {row['inflation']:.2f}%")
    
    # Extract U-3 slack (same as baseline)
    print(f"\n📉 Extracting U-3 unemployment rate...")
    slack_u3 = compute_slack(slack_data=slack_df, reference_period=reference_period)
    print(f"  U-3 Rate: {slack_u3:.1f}%")
    
    # Compute DMI with core inflation
    print(f"\n💡 Computing DMI with Core CPI...")
    dmi_df = compute_dmi(
        inflation_by_group=inflation_df,
        slack=slack_u3,
        alpha=0.5,
        scale_factor=2.0
    )
    
    print(f"\n  DMI by Income Quintile (Core CPI):")
    for _, row in dmi_df.iterrows():
        print(f"    {row['group_id']}: DMI={row['dmi']:6.2f}  (core_inflation={row['inflation']:5.2f}%, slack={row['slack']:4.1f}%)")
    
    # Summary metrics
    metrics = compute_summary_metrics(dmi_df)
    
    # Compile results
    results = {
        "reference_period": reference_period,
        "specification": "CORE_CPI",
        "description": "DMI computed using Core CPI (excluding food and beverages)",
        "parameters": {
            "alpha": 0.5,
            "scale_factor": 2.0,
            "weights_year": 2023,
            "inflation_measure": "CORE_CPI",
            "excluded_categories": ["CPI_FOOD_BEVERAGES"]
        },
        "dmi_by_group": dmi_df.to_dict(orient='records'),
        "summary_metrics": metrics,
        "inflation_contributions": contributions_df.to_dict(orient='records'),
        "metadata": {
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "num_groups": len(dmi_df),
            "note": "Core CPI excludes volatile food and beverage prices"
        }
    }
    
    # Save results
    output_dir = data_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"dmi_release_{reference_period}_core.json"
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    # Generate comparison report
    print(f"\n" + "=" * 80)
    print("COMPARISON: Core CPI vs Headline CPI (Baseline)")
    print("=" * 80)
    
    # Load baseline results if available
    baseline_file = output_dir / f"dmi_release_{reference_period}.json"
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline = json.load(f)
        
        print(f"\nInflation Comparison:")
        print(f"  {'Quintile':<10} {'Headline':<12} {'Core':<12} {'Difference':<12} {'Food Impact'}")
        print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
        
        for i, core_row in enumerate(results['dmi_by_group']):
            baseline_row = baseline['dmi_by_group'][i]
            infl_diff = core_row['inflation'] - baseline_row['inflation']
            # Negative difference means food inflated faster than core
            print(f"  {core_row['group_id']:<10} {baseline_row['inflation']:>11.2f}%  {core_row['inflation']:>11.2f}%  {infl_diff:>+11.2f}pp  {'Higher' if infl_diff < -0.1 else 'Lower' if infl_diff > 0.1 else 'Similar'}")
        
        print(f"\nDMI Comparison:")
        print(f"  {'Quintile':<10} {'Headline DMI':<14} {'Core DMI':<14} {'Difference'}")
        print(f"  {'-'*10} {'-'*14} {'-'*14} {'-'*10}")
        
        for i, core_row in enumerate(results['dmi_by_group']):
            baseline_row = baseline['dmi_by_group'][i]
            dmi_diff = core_row['dmi'] - baseline_row['dmi']
            print(f"  {core_row['group_id']:<10} {baseline_row['dmi']:>13.2f}  {core_row['dmi']:>13.2f}  {dmi_diff:>+9.2f}")
        
        avg_diff = sum(core_row['dmi'] - baseline['dmi_by_group'][i]['dmi'] 
                      for i, core_row in enumerate(results['dmi_by_group'])) / len(results['dmi_by_group'])
        
        print(f"\n  Average DMI difference (Core - Headline): {avg_diff:+.2f} points")
        
        # Analysis
        q1_diff = results['dmi_by_group'][0]['dmi'] - baseline['dmi_by_group'][0]['dmi']
        q5_diff = results['dmi_by_group'][4]['dmi'] - baseline['dmi_by_group'][4]['dmi']
        
        print(f"\n💡 Interpretation:")
        if abs(avg_diff) < 0.5:
            print(f"  Core and headline DMI are very similar (±0.5 points).")
            print(f"  Food price volatility has minimal impact on overall DMI.")
        else:
            print(f"  Core DMI differs from headline by {abs(avg_diff):.1f} points.")
            if avg_diff < 0:
                print(f"  Food prices inflated faster than core items this period.")
            else:
                print(f"  Core items inflated faster than food this period.")
        
        if abs(q1_diff - q5_diff) > 0.2:
            print(f"  Lower-income quintiles are more sensitive to food price changes")
            print(f"  (Q1 difference: {q1_diff:+.2f}, Q5 difference: {q5_diff:+.2f}).")
    else:
        print(f"\n⚠️  Baseline results not found at: {baseline_file}")
        print(f"  Run compute_dmi.py first to generate comparison.")
    
    print(f"\n" + "=" * 80)
    print("✓ Core CPI alternative specification complete!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
