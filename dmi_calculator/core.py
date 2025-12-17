"""
DMI Calculator - Core deterministic functions.

This module implements the pure, category-agnostic calculation logic for the
Distributional Misery Index (DMI) v0.1.

Principles:
- No I/O operations (all inputs passed as arguments)
- Deterministic (same inputs → identical outputs)
- Category-agnostic (keys off category_id, not hard-coded labels)
- Pure functions (no side effects)

Formula: DMI(g,r,t) = scale_factor × [α × π(g,r,t) + (1-α) × S(r,t)]
where:
- π(g,r,t) = group-weighted inflation (YoY log change)
- S(r,t) = labor market slack (unemployment rate)
- α = 0.5 (default)
- scale_factor = 2.0 (default)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional


def compute_group_weighted_inflation(
    cpi_levels: pd.DataFrame,
    weights: pd.DataFrame,
    reference_period: str,
    horizon_months: int = 12,
    method: str = "log_change_weighted"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute group-weighted inflation π(g,r,t) for each income group.
    
    Args:
        cpi_levels: DataFrame with columns [period, category_id_1, category_id_2, ...]
                   Index levels for each CPI category by period.
        weights: DataFrame with columns [group_id, category_id, weight]
                Weight/share for each group × category combination.
        reference_period: Period to compute inflation for (YYYY-MM format)
        horizon_months: Number of months for YoY comparison (default: 12)
        method: Aggregation method (default: "log_change_weighted")
    
    Returns:
        Tuple of (inflation_by_group, contributions_by_group_category):
        - inflation_by_group: DataFrame with columns [group_id, inflation]
        - contributions: DataFrame with columns [group_id, category_id, contribution]
    
    Raises:
        ValueError: If required data is missing or malformed
    """
    # Parse reference period
    ref_year, ref_month = map(int, reference_period.split('-'))
    
    # Calculate base period (t-horizon_months)
    base_date = pd.to_datetime(reference_period) - pd.DateOffset(months=horizon_months)
    base_period = base_date.strftime('%Y-%m')
    
    # Get CPI levels for reference and base periods
    cpi_ref = cpi_levels[cpi_levels['period'] == reference_period]
    cpi_base = cpi_levels[cpi_levels['period'] == base_period]
    
    if cpi_ref.empty:
        raise ValueError(f"No CPI data for reference period {reference_period}")
    if cpi_base.empty:
        raise ValueError(f"No CPI data for base period {base_period}")
    
    # Get category columns (exclude 'period')
    category_cols = [col for col in cpi_levels.columns if col != 'period']
    
    # Validate category coverage
    missing_cats = set(weights['category_id'].unique()) - set(category_cols)
    if missing_cats:
        raise ValueError(f"Missing CPI data for categories: {missing_cats}")
    
    # Compute price relatives: rel(c,t) = CPI(c,t) / CPI(c,t-12)
    price_relatives = {}
    for cat in category_cols:
        cpi_t = cpi_ref[cat].values[0]
        cpi_t_minus_12 = cpi_base[cat].values[0]
        price_relatives[cat] = cpi_t / cpi_t_minus_12
    
    # Compute weighted log inflation for each group
    inflation_results = []
    contributions_results = []
    
    for group_id in weights['group_id'].unique():
        group_weights = weights[weights['group_id'] == group_id]
        
        # Validate weights sum to 1.0 (with tolerance)
        weights_sum = group_weights['weight'].sum()
        if abs(weights_sum - 1.0) > 0.001:
            raise ValueError(
                f"Weights for {group_id} sum to {weights_sum:.4f}, expected 1.0 ± 0.001"
            )
        
        # Compute: log_rel(g,t) = Σ_c w(g,c) · ln(rel(c,t))
        log_sum = 0.0
        log_rels = {}
        
        for _, row in group_weights.iterrows():
            cat_id = row['category_id']
            weight = row['weight']
            rel = price_relatives[cat_id]
            
            log_rel = np.log(rel)
            log_rels[cat_id] = log_rel
            log_sum += weight * log_rel
        
        # Convert to percentage: π(g,t) = 100 · (exp(log_rel) − 1)
        inflation_pct = 100.0 * (np.exp(log_sum) - 1.0)
        
        # Compute contributions that sum to total
        # Using linear approximation in log space: contribution ≈ 100 · w(g,c) · ln(rel(c,t))
        # But scale to ensure they sum exactly to inflation_pct
        naive_contributions = {cat_id: 100.0 * w * log_rels[cat_id] 
                              for cat_id, w in zip(group_weights['category_id'], group_weights['weight'])}
        naive_sum = sum(naive_contributions.values())
        
        # Scale contributions to match total (handles Taylor approximation error)
        if naive_sum != 0:
            scale_factor_contrib = inflation_pct / naive_sum
        else:
            scale_factor_contrib = 1.0
        
        group_contributions = []
        for cat_id, naive_contrib in naive_contributions.items():
            contribution = naive_contrib * scale_factor_contrib
            group_contributions.append({
                'group_id': group_id,
                'category_id': cat_id,
                'contribution': contribution
            })
        
        inflation_results.append({
            'group_id': group_id,
            'inflation': inflation_pct
        })
        
        contributions_results.extend(group_contributions)
    
    inflation_df = pd.DataFrame(inflation_results)
    contributions_df = pd.DataFrame(contributions_results)
    
    return inflation_df, contributions_df


def compute_slack(
    slack_data: pd.DataFrame,
    reference_period: str,
    geo_id: str = "US"
) -> float:
    """
    Extract labor market slack S(r,t) for a geography and period.
    
    Args:
        slack_data: DataFrame with columns [period, value, geo_id (optional)]
        reference_period: Period to extract slack for (YYYY-MM format)
        geo_id: Geography identifier (default: "US")
    
    Returns:
        Slack value (unemployment rate as percentage)
    
    Raises:
        ValueError: If slack data is missing for period
    """
    # Filter by geo_id if column exists
    if 'geo_id' in slack_data.columns:
        geo_slack = slack_data[slack_data['geo_id'] == geo_id]
    else:
        geo_slack = slack_data
    
    # Get slack for reference period
    period_slack = geo_slack[geo_slack['period'] == reference_period]
    
    if period_slack.empty:
        raise ValueError(
            f"No slack data for period {reference_period}, geo {geo_id}"
        )
    
    return float(period_slack['value'].values[0])


def compute_dmi(
    inflation_by_group: pd.DataFrame,
    slack: float,
    alpha: float = 0.5,
    scale_factor: float = 2.0
) -> pd.DataFrame:
    """
    Compute Distributional Misery Index (DMI) for each group.
    
    Formula: DMI(g) = scale_factor × [α × π(g) + (1-α) × S]
    
    Args:
        inflation_by_group: DataFrame with columns [group_id, inflation]
        slack: Slack value (same for all groups in v0.1)
        alpha: Weight for inflation vs slack (default: 0.5)
        scale_factor: Scaling factor (default: 2.0)
    
    Returns:
        DataFrame with columns [group_id, dmi, inflation, slack]
    """
    results = []
    
    for _, row in inflation_by_group.iterrows():
        group_id = row['group_id']
        inflation = row['inflation']
        
        # DMI formula
        dmi = scale_factor * (alpha * inflation + (1 - alpha) * slack)
        
        results.append({
            'group_id': group_id,
            'dmi': dmi,
            'inflation': inflation,
            'slack': slack
        })
    
    return pd.DataFrame(results)


def compute_summary_metrics(
    dmi_by_group: pd.DataFrame
) -> Dict[str, float]:
    """
    Compute summary metrics for DMI distribution.
    
    Args:
        dmi_by_group: DataFrame with columns [group_id, dmi, ...]
    
    Returns:
        Dictionary with keys:
        - dmi_median: Median DMI (typically Q3 for quintiles)
        - dmi_stress: Maximum DMI across groups
        - dmi_dispersion_q5_q1: Q5 - Q1 (for quintiles)
    """
    dmi_values = dmi_by_group['dmi'].values
    
    # Sort group_ids to get Q1-Q5 ordering
    sorted_groups = dmi_by_group.sort_values('group_id')
    
    metrics = {
        'dmi_median': float(np.median(dmi_values)),
        'dmi_stress': float(np.max(dmi_values))
    }
    
    # Dispersion (Q5 - Q1) if quintiles present
    if 'Q5' in sorted_groups['group_id'].values and 'Q1' in sorted_groups['group_id'].values:
        q5_dmi = float(sorted_groups[sorted_groups['group_id'] == 'Q5']['dmi'].values[0])
        q1_dmi = float(sorted_groups[sorted_groups['group_id'] == 'Q1']['dmi'].values[0])
        metrics['dmi_dispersion_q5_q1'] = q5_dmi - q1_dmi
    
    return metrics


def validate_contributions_sum_to_total(
    contributions: pd.DataFrame,
    inflation_by_group: pd.DataFrame,
    tolerance: float = 0.01
) -> bool:
    """
    Validate that inflation contributions sum to total inflation for each group.
    
    Args:
        contributions: DataFrame with columns [group_id, category_id, contribution]
        inflation_by_group: DataFrame with columns [group_id, inflation]
        tolerance: Acceptable difference (default: 0.01 percentage points)
    
    Returns:
        True if valid, False otherwise
    
    Raises:
        AssertionError: If contributions don't sum to total within tolerance
    """
    for group_id in contributions['group_id'].unique():
        group_contribs = contributions[contributions['group_id'] == group_id]
        contrib_sum = group_contribs['contribution'].sum()
        
        total_inflation = inflation_by_group[
            inflation_by_group['group_id'] == group_id
        ]['inflation'].values[0]
        
        diff = abs(contrib_sum - total_inflation)
        if diff > tolerance:
            raise AssertionError(
                f"Contributions for {group_id} sum to {contrib_sum:.4f}, "
                f"but total inflation is {total_inflation:.4f} (diff: {diff:.4f})"
            )
    
    return True
