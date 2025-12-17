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

import pandas as pd

from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics,
    validate_contributions_sum_to_total
)
from dmi_pipeline.agents.qa_validator import generate_qa_report, print_qa_summary


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
    print(f"      Dispersion (Q5-Q1): {metrics['dmi_dispersion_q5_q1']:.2f}")
    
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


def main():
    print("=" * 80)
    print("DMI v0.1.8 - Full Integration Test")
    print("=" * 80)
    
    # Paths
    weights_path = Path("data/curated/weights_by_group_2023.json")
    cpi_path = Path("data/staging/cpi_levels_2023_2024.json")
    slack_path = Path("data/staging/slack_u3_2023_2024.json")
    
    # Load data
    print("\nLoading data...")
    weights_df = load_weights(weights_path)
    print(f"  ✓ Weights: {len(weights_df)} records (5 quintiles × 8 categories)")
    
    cpi_df = load_cpi_data(cpi_path)
    print(f"  ✓ CPI data: {len(cpi_df)} periods, 8 categories")
    
    slack_df = load_slack_data(slack_path)
    print(f"  ✓ Slack data: {len(slack_df)} periods")
    
    # Compute DMI for November 2024
    print("\n" + "=" * 80)
    reference_period = "2024-11"
    
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
    print(f"  Dispersion (Q5-Q1): {results['summary_metrics']['dmi_dispersion_q5_q1']:.2f}")
    
    print("\n" + "=" * 80)
    print("✓ Full DMI integration test completed successfully!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
