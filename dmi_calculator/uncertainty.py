"""
Uncertainty Quantification for DMI

Provides confidence interval estimation using bootstrap simulation
to quantify uncertainty from Consumer Expenditure Survey sampling error.

Bootstrap Approach:
1. Perturb CE weights within assumed sampling distribution
2. Recompute DMI with perturbed weights
3. Repeat 1000 times
4. Report 95% confidence intervals (2.5th to 97.5th percentile)

Limitations:
- Assumes coefficient of variation (CV) for CE weights (default: 5%)
- Only captures weight uncertainty, not CPI or unemployment uncertainty
- Simplified approach in absence of published CE standard errors
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict
from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics
)


def perturb_weights(
    weights_df: pd.DataFrame,
    weight_cv: float = 0.05,
    random_state: int = None
) -> pd.DataFrame:
    """
    Perturb CE weights by drawing from normal distribution.
    
    Args:
        weights_df: Original CE weights DataFrame
        weight_cv: Coefficient of variation (std/mean) for weights
        random_state: Random seed for reproducibility
        
    Returns:
        Perturbed weights DataFrame with same structure
    """
    rng = np.random.RandomState(random_state)
    perturbed = weights_df.copy()
    
    # Perturb each weight: w ~ N(w_original, w_original * cv)
    for idx in perturbed.index:
        original_weight = perturbed.loc[idx, 'weight']
        std_dev = original_weight * weight_cv
        
        # Draw from normal, ensure positive
        perturbed_weight = rng.normal(original_weight, std_dev)
        perturbed_weight = max(0.001, perturbed_weight)  # Floor at 0.1%
        
        perturbed.loc[idx, 'weight'] = perturbed_weight
    
    # Renormalize so each group's weights sum to 1.0
    for group_id in perturbed['group_id'].unique():
        group_mask = perturbed['group_id'] == group_id
        weight_sum = perturbed.loc[group_mask, 'weight'].sum()
        perturbed.loc[group_mask, 'weight'] = perturbed.loc[group_mask, 'weight'] / weight_sum
    
    return perturbed


def bootstrap_dmi(
    cpi_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    slack_df: pd.DataFrame,
    reference_period: str,
    n_bootstrap: int = 1000,
    weight_cv: float = 0.05,
    alpha: float = 0.5,
    scale_factor: float = 2.0,
    random_seed: int = None
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Compute DMI with bootstrap confidence intervals.
    
    Args:
        cpi_df: CPI levels DataFrame
        weights_df: CE weights DataFrame
        slack_df: Unemployment data DataFrame
        reference_period: Period to compute (e.g., "2024-11")
        n_bootstrap: Number of bootstrap iterations
        weight_cv: Coefficient of variation for weight perturbation
        alpha: DMI parameter (inflation weight)
        scale_factor: DMI scaling parameter
        random_seed: Random seed for reproducibility
        
    Returns:
        - dmi_with_ci: DataFrame with point estimates and CI bounds
        - bootstrap_samples: Array of shape (n_bootstrap, n_groups) for analysis
    """
    print(f"  Running {n_bootstrap} bootstrap iterations...")
    
    # Extract slack (constant across bootstrap samples)
    slack = compute_slack(slack_data=slack_df, reference_period=reference_period)
    
    # Storage for bootstrap results
    groups = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    bootstrap_dmi = np.zeros((n_bootstrap, len(groups)))
    bootstrap_inflation = np.zeros((n_bootstrap, len(groups)))
    
    # Bootstrap iterations
    for i in range(n_bootstrap):
        if (i + 1) % 200 == 0:
            print(f"    Progress: {i+1}/{n_bootstrap}")
        
        # Perturb weights
        seed = random_seed + i if random_seed is not None else None
        perturbed_weights = perturb_weights(weights_df, weight_cv, seed)
        
        # Compute inflation with perturbed weights
        inflation_df, _ = compute_group_weighted_inflation(
            cpi_levels=cpi_df,
            weights=perturbed_weights,
            reference_period=reference_period,
            horizon_months=12
        )
        
        # Compute DMI
        dmi_df = compute_dmi(
            inflation_by_group=inflation_df,
            slack=slack,
            alpha=alpha,
            scale_factor=scale_factor
        )
        
        # Store results
        for j, group in enumerate(groups):
            group_row = dmi_df[dmi_df['group_id'] == group].iloc[0]
            bootstrap_dmi[i, j] = group_row['dmi']
            bootstrap_inflation[i, j] = group_row['inflation']
    
    # Compute statistics from bootstrap distribution
    results = []
    for j, group in enumerate(groups):
        dmi_samples = bootstrap_dmi[:, j]
        inflation_samples = bootstrap_inflation[:, j]
        
        results.append({
            'group_id': group,
            'dmi': np.median(dmi_samples),  # Point estimate: median
            'dmi_ci_lower': np.percentile(dmi_samples, 2.5),  # 95% CI lower
            'dmi_ci_upper': np.percentile(dmi_samples, 97.5),  # 95% CI upper
            'dmi_se': np.std(dmi_samples),  # Standard error
            'inflation': np.median(inflation_samples),
            'inflation_ci_lower': np.percentile(inflation_samples, 2.5),
            'inflation_ci_upper': np.percentile(inflation_samples, 97.5),
            'inflation_se': np.std(inflation_samples),
            'slack': slack
        })
    
    dmi_with_ci = pd.DataFrame(results)
    
    print(f"  ✓ Bootstrap complete")
    return dmi_with_ci, bootstrap_dmi


def compute_dmi_with_confidence_intervals(
    cpi_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    slack_df: pd.DataFrame,
    reference_period: str,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    weight_cv: float = 0.05,
    alpha: float = 0.5,
    scale_factor: float = 2.0,
    random_seed: int = 42
) -> Dict:
    """
    High-level function to compute DMI with confidence intervals.
    
    Returns complete results dictionary including point estimates,
    confidence intervals, and bootstrap metadata.
    
    Args:
        cpi_df: CPI levels DataFrame
        weights_df: CE weights DataFrame  
        slack_df: Unemployment data DataFrame
        reference_period: Period to compute
        n_bootstrap: Number of bootstrap iterations (default: 1000)
        confidence_level: CI level (default: 0.95)
        weight_cv: Assumed CV for CE weights (default: 0.05 = 5%)
        alpha: DMI inflation weight parameter
        scale_factor: DMI scaling parameter
        random_seed: Random seed for reproducibility
        
    Returns:
        Dictionary with dmi_by_group (with CIs), summary_metrics, and metadata
    """
    print(f"\n{'='*80}")
    print(f"Computing DMI with {int(confidence_level*100)}% Confidence Intervals")
    print(f"{'='*80}")
    print(f"  Period: {reference_period}")
    print(f"  Bootstrap iterations: {n_bootstrap}")
    print(f"  Weight CV assumption: {weight_cv*100:.1f}%")
    print()
    
    # Run bootstrap
    dmi_with_ci, bootstrap_samples = bootstrap_dmi(
        cpi_df=cpi_df,
        weights_df=weights_df,
        slack_df=slack_df,
        reference_period=reference_period,
        n_bootstrap=n_bootstrap,
        weight_cv=weight_cv,
        alpha=alpha,
        scale_factor=scale_factor,
        random_seed=random_seed
    )
    
    # Compute summary metrics (using point estimates)
    dmi_point_estimates = dmi_with_ci[['group_id', 'dmi', 'inflation', 'slack']].copy()
    summary = compute_summary_metrics(dmi_point_estimates)
    
    # Display results
    print(f"\n{'='*80}")
    print("Results with Confidence Intervals:")
    print(f"{'='*80}\n")
    
    for _, row in dmi_with_ci.iterrows():
        ci_width = row['dmi_ci_upper'] - row['dmi_ci_lower']
        print(f"  {row['group_id']}: DMI = {row['dmi']:.2f} "
              f"[{row['dmi_ci_lower']:.2f}, {row['dmi_ci_upper']:.2f}] "
              f"(SE={row['dmi_se']:.3f}, width={ci_width:.2f})")
    
    print(f"\nInflation with Confidence Intervals:")
    for _, row in dmi_with_ci.iterrows():
        ci_width = row['inflation_ci_upper'] - row['inflation_ci_lower']
        print(f"  {row['group_id']}: Inflation = {row['inflation']:.2f}% "
              f"[{row['inflation_ci_lower']:.2f}%, {row['inflation_ci_upper']:.2f}%] "
              f"(SE={row['inflation_se']:.3f}%, width={ci_width:.2f}%)")
    
    print(f"\n💡 Interpretation:")
    avg_ci_width = (dmi_with_ci['dmi_ci_upper'] - dmi_with_ci['dmi_ci_lower']).mean()
    print(f"  Average 95% CI width: {avg_ci_width:.2f} DMI points")
    print(f"  This reflects uncertainty from CE weights sampling error only.")
    print(f"  Actual uncertainty is higher (CPI and unemployment also have sampling error).")
    
    # Compile results
    results = {
        'reference_period': reference_period,
        'specification': 'BASELINE_WITH_CI',
        'description': f'DMI with {int(confidence_level*100)}% bootstrap confidence intervals',
        'parameters': {
            'alpha': alpha,
            'scale_factor': scale_factor,
            'n_bootstrap': n_bootstrap,
            'confidence_level': confidence_level,
            'weight_cv': weight_cv,
            'random_seed': random_seed
        },
        'dmi_by_group': dmi_with_ci.to_dict(orient='records'),
        'summary_metrics': summary,
        'metadata': {
            'note': 'Confidence intervals reflect CE weights uncertainty only (not CPI or unemployment)',
            'assumption': f'CE weights assumed CV = {weight_cv*100:.1f}%',
            'method': 'Bootstrap simulation with weight perturbation'
        }
    }
    
    return results
