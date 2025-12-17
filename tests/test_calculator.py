"""
Unit tests for DMI Calculator core functions.

Tests use fixture data to validate:
- Group-weighted inflation calculation  
- Slack extraction
- DMI formula
- Summary metrics
- Validation functions
- Category-agnostic behavior
"""

import pytest
import pandas as pd
import numpy as np
import json
from pathlib import Path

from dmi_calculator.core import (
    compute_group_weighted_inflation,
    compute_slack,
    compute_dmi,
    compute_summary_metrics,
    validate_contributions_sum_to_total
)


# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def cpi_data():
    """Load sample CPI levels."""
    with open(FIXTURES_DIR / "sample_cpi_levels.json") as f:
        data = json.load(f)
    return pd.DataFrame(data['data'])


@pytest.fixture
def weights_data():
    """Load sample weights."""
    with open(FIXTURES_DIR / "sample_weights.json") as f:
        data = json.load(f)
    return pd.DataFrame(data['rows'])


@pytest.fixture
def slack_data():
    """Load sample slack data."""
    with open(FIXTURES_DIR / "sample_slack.json") as f:
        data = json.load(f)
    return pd.DataFrame(data['data'])


class TestGroupWeightedInflation:
    """Tests for compute_group_weighted_inflation function."""
    
    def test_inflation_calculation_2024_11(self, cpi_data, weights_data):
        """Test inflation calculation for 2024-11 (YoY from 2023-11)."""
        inflation_df, contributions_df = compute_group_weighted_inflation(
            cpi_levels=cpi_data,
            weights=weights_data,
            reference_period="2024-11",
            horizon_months=12
        )
        
        # Should have 5 quintiles
        assert len(inflation_df) == 5
        assert set(inflation_df['group_id']) == {'Q1', 'Q2', 'Q3', 'Q4', 'Q5'}
        
        # Inflation should be positive (given fixture data has growth)
        assert all(inflation_df['inflation'] > 0)
        
        # Should be roughly in 3-7% range (based on fixture CPI growth)
        assert all(inflation_df['inflation'] < 10)
        
    def test_contributions_sum_to_total(self, cpi_data, weights_data):
        """Test that category contributions sum to total group inflation."""
        inflation_df, contributions_df = compute_group_weighted_inflation(
            cpi_data, weights_data, "2024-11"
        )
        
        # Validate contributions
        assert validate_contributions_sum_to_total(
            contributions_df, inflation_df, tolerance=0.01
        )
    
    def test_category_agnostic_behavior(self, cpi_data):
        """Test that calculator works with any category_ids (no hard-coding)."""
        # Create weights with different category names
        custom_weights = pd.DataFrame([
            {"group_id": "G1", "category_id": "CPI_FOOD_BEVERAGES", "weight": 0.5},
            {"group_id": "G1", "category_id": "CPI_HOUSING", "weight": 0.5},
        ])
        
        # Should work without error
        inflation_df, contribs = compute_group_weighted_inflation(
            cpi_data, custom_weights, "2024-11"
        )
        
        assert len(inflation_df) == 1
        assert inflation_df.iloc[0]['group_id'] == "G1"
    
    def test_missing_cpi_data_raises_error(self, cpi_data, weights_data):
        """Test that missing CPI data raises appropriate error."""
        with pytest.raises(ValueError, match="No CPI data for reference period"):
            compute_group_weighted_inflation(
                cpi_data, weights_data, "2025-01"  # Future period
            )
    
    def test_weights_must_sum_to_one(self, cpi_data):
        """Test that weights validation enforces sum=1.0."""
        bad_weights = pd.DataFrame([
            {"group_id": "Q1", "category_id": "CPI_FOOD_BEVERAGES", "weight": 0.3},
            {"group_id": "Q1", "category_id": "CPI_HOUSING", "weight": 0.3},
            # Total = 0.6, should fail
        ])
        
        with pytest.raises(ValueError, match="sum to"):
            compute_group_weighted_inflation(
                cpi_data, bad_weights, "2024-11"
            )


class TestSlackComputation:
    """Tests for compute_slack function."""
    
    def test_slack_extraction(self, slack_data):
        """Test extracting slack for a specific period."""
        slack = compute_slack(slack_data, "2024-11", geo_id="US")
        
        # From fixture: 2024-11 = 4.2
        assert slack == 4.2
    
    def test_missing_slack_period_raises_error(self, slack_data):
        """Test that missing period raises error."""
        with pytest.raises(ValueError, match="No slack data"):
            compute_slack(slack_data, "2025-01", geo_id="US")


class TestDMIComputation:
    """Tests for compute_dmi function."""
    
    def test_dmi_formula(self):
        """Test DMI formula: scale_factor × [α × π + (1-α) × S]."""
        inflation_df = pd.DataFrame([
            {"group_id": "Q1", "inflation": 5.0},
            {"group_id": "Q2", "inflation": 4.0},
        ])
        
        slack = 4.0
        alpha = 0.5
        scale_factor = 2.0
        
        dmi_df = compute_dmi(inflation_df, slack, alpha, scale_factor)
        
        # DMI(Q1) = 2.0 × [0.5 × 5.0 + 0.5 × 4.0] = 2.0 × 4.5 = 9.0
        assert abs(dmi_df[dmi_df['group_id'] == 'Q1']['dmi'].values[0] - 9.0) < 0.01
        
        # DMI(Q2) = 2.0 × [0.5 × 4.0 + 0.5 × 4.0] = 2.0 × 4.0 = 8.0
        assert abs(dmi_df[dmi_df['group_id'] == 'Q2']['dmi'].values[0] - 8.0) < 0.01
    
    def test_dmi_preserves_slack(self):
        """Test that slack value is preserved in output."""
        inflation_df = pd.DataFrame([
            {"group_id": "Q1", "inflation": 5.0},
        ])
        
        dmi_df = compute_dmi(inflation_df, slack=3.7)
        assert dmi_df.iloc[0]['slack'] == 3.7


class TestSummaryMetrics:
    """Tests for compute_summary_metrics function."""
    
    def test_summary_metrics_quintiles(self):
        """Test summary metrics calculation for quintiles."""
        dmi_df = pd.DataFrame([
            {"group_id": "Q1", "dmi": 10.0},
            {"group_id": "Q2", "dmi": 9.0},
            {"group_id": "Q3", "dmi": 8.5},
            {"group_id": "Q4", "dmi": 8.0},
            {"group_id": "Q5", "dmi": 7.0},
        ])
        
        metrics = compute_summary_metrics(dmi_df)
        
        # Median should be 8.5 (middle value)
        assert metrics['dmi_median'] == 8.5
        
        # Stress should be max = 10.0
        assert metrics['dmi_stress'] == 10.0
        
        # Dispersion = Q5 - Q1 = 7.0 - 10.0 = -3.0
        assert metrics['dmi_dispersion_q5_q1'] == -3.0


class TestEndToEndCalculation:
    """End-to-end tests with fixture data."""
    
    def test_full_pipeline_2024_11(self, cpi_data, weights_data, slack_data):
        """Test complete pipeline for 2024-11."""
        # Step 1: Compute inflation
        inflation_df, contributions_df = compute_group_weighted_inflation(
            cpi_data, weights_data, "2024-11"
        )
        
        # Step 2: Extract slack
        slack = compute_slack(slack_data, "2024-11")
        
        # Step 3: Compute DMI
        dmi_df = compute_dmi(inflation_df, slack)
        
        # Step 4: Summary metrics
        metrics = compute_summary_metrics(dmi_df)
        
        # Validations
        assert len(dmi_df) == 5  # 5 quintiles
        assert'dmi' in dmi_df.columns
        assert 'inflation' in dmi_df.columns
        assert 'slack' in dmi_df.columns
        
        assert 'dmi_median' in metrics
        assert 'dmi_stress' in metrics
        assert 'dmi_dispersion_q5_q1' in metrics
        
        # DMI should be higher than individual components
        assert all(dmi_df['dmi'] > 0)
        
        # Validate contributions
        assert validate_contributions_sum_to_total(contributions_df, inflation_df)
    
    def test_determinism(self, cpi_data, weights_data, slack_data):
        """Test that same inputs produce identical outputs."""
        # Run calculation twice
        result1_inflation, result1_contribs = compute_group_weighted_inflation(
            cpi_data, weights_data, "2024-11"
        )
        result1_slack = compute_slack(slack_data, "2024-11")
        result1_dmi = compute_dmi(result1_inflation, result1_slack)
        
        result2_inflation, result2_contribs = compute_group_weighted_inflation(
            cpi_data, weights_data, "2024-11"
        )
        result2_slack = compute_slack(slack_data, "2024-11")
        result2_dmi = compute_dmi(result2_inflation, result2_slack)
        
        # Results should be bitwise identical
        pd.testing.assert_frame_equal(result1_dmi, result2_dmi)
        pd.testing.assert_frame_equal(result1_inflation, result2_inflation)
        assert result1_slack == result2_slack
