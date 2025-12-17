"""
Unit tests for CE Weights Pipeline.

Tests CE table download, validation, extraction, and mapping.
"""

import pytest
import json
from pathlib import Path
import tempfile
import shutil

from dmi_pipeline.agents.ce_harvester import (
    download_ce_table,
    validate_ce_table_structure
)
from dmi_pipeline.agents.ce_weights_builder import (
    extract_weights_from_ce_table,
    save_weights_to_file
)


# Fixtures
REGISTRY_DIR = Path(__file__).parent.parent / "registry"


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def ce_mapping_path():
    """Path to CE→CPI mapping artifact."""
    return REGISTRY_DIR / "artifacts" / "ce_table_to_cpi_mapping_v0_1.json"


@pytest.fixture
def ce_policy_path():
    """Path to CE weights policy."""
    return REGISTRY_DIR / "policies" / "ce_weights_policy_v0_1.json"


@pytest.fixture
def expected_ce_labels(ce_policy_path):
    """Load expected CE item labels from policy."""
    with open(ce_policy_path) as f:
        policy = json.load(f)
    return policy['expected_ce_item_labels']


class TestCETableDownload:
    """Tests for CE table download function."""
    
    @pytest.mark.skip(reason="Requires network; run manually")
    def test_download_quintile_2023(self, temp_data_dir):
        """Test downloading 2023 quintile table."""
        file_path, checksum = download_ce_table(
            year=2023,
            table_type="quintile",
            output_dir=str(temp_data_dir)
        )
        
        assert file_path.exists()
        assert file_path.suffix == ".xlsx"
        assert len(checksum) == 64  # SHA256 hex length
        assert file_path.stat().st_size > 10000  # Non-trivial file
    
    def test_invalid_table_type(self, temp_data_dir):
        """Test that invalid table type raises error."""
        with pytest.raises(ValueError, match="table_type must be"):
            download_ce_table(
                year=2023,
                table_type="invalid",
                output_dir=str(temp_data_dir)
            )


class TestCETableValidation:
    """Tests for CE table structural validation."""
    
    @pytest.mark.skip(reason="Requires downloaded CE table")
    def test_validation_on_real_table(self, temp_data_dir, expected_ce_labels):
        """Test validation on actual 2023 CE table."""
        # Download table first
        file_path, _ = download_ce_table(
            year=2023,
            table_type="quintile",
            output_dir=str(temp_data_dir)
        )
        
        # Validate
        result = validate_ce_table_structure(
            file_path,
            expected_table_type="quintile",
            expected_item_labels=expected_ce_labels
        )
        
        # Should pass all checks
        assert result['status'] in ['PASS', 'PASS_WITH_WARNING']
        assert len(result['checks']) == 4  # 4 validation checks
        
        # Check IDs should be present
        check_ids = [c['check_id'] for c in result['checks']]
        assert 'CE_XLSX_EXPECTED_ITEM_LABELS_PRESENT' in check_ids
        assert 'CE_XLSX_MEAN_SHARE_ROW_PAIRING' in check_ids
        assert 'CE_XLSX_GROUP_COLUMN_COUNT' in check_ids
        assert 'CE_XLSX_SHARE_RANGE_SANITY' in check_ids


class TestWeightsExtraction:
    """Tests for weights extraction and mapping."""
    
    @pytest.mark.skip(reason="Requires downloaded CE table")
    def test_extract_weights_from_2023_table(self, temp_data_dir, ce_mapping_path):
        """Test extracting weights from actual 2023 table."""
        # Download table
        file_path, _ = download_ce_table(
            year=2023,
            table_type="quintile",
            output_dir=str(temp_data_dir)
        )
        
        # Extract weights
        weights_df = extract_weights_from_ce_table(
            file_path,
            table_type="quintile",
            mapping_path=ce_mapping_path
        )
        
        # Validate structure
        assert len(weights_df) > 0
        assert set(weights_df.columns) >= {'group_id', 'category_id', 'weight'}
        
        # Should have 5 quintiles
        assert set(weights_df['group_id'].unique()) == {'Q1', 'Q2', 'Q3', 'Q4', 'Q5'}
        
        # Should have 8 CPI categories
        expected_cats = {
            'CPI_FOOD_BEVERAGES', 'CPI_HOUSING', 'CPI_APPAREL',
            'CPI_TRANSPORTATION', 'CPI_MEDICAL_CARE', 'CPI_RECREATION',
            'CPI_EDU_COMM', 'CPI_OTHER'
        }
        assert set(weights_df['category_id'].unique()) == expected_cats
        
        # Weights should sum to 1.0 per group
        for group_id in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
            group_sum = weights_df[weights_df['group_id'] == group_id]['weight'].sum()
            assert abs(group_sum - 1.0) < 0.001, f"{group_id} weights sum to {group_sum}"
        
        # Weights should be non-negative
        assert all(weights_df['weight'] >= 0)
    
    @pytest.mark.skip(reason="Requires downloaded CE table")
    def test_save_weights_to_json(self, temp_data_dir, ce_mapping_path):
        """Test saving weights to JSON format."""
        # Download and extract
        file_path, _ = download_ce_table(
            year=2023,
            table_type="quintile",
            output_dir=str(temp_data_dir)
        )
        
        weights_df = extract_weights_from_ce_table(
            file_path,
            table_type="quintile",
            mapping_path=ce_mapping_path
        )
        
        # Save to JSON
        output_path = temp_data_dir / "weights_2023.json"
        save_weights_to_file(
            weights_df,
            output_path,
            weights_year=2023,
            table_type="quintile",
            metadata={"source": "test"}
        )
        
        # Load and validate JSON
        assert output_path.exists()
        with open(output_path) as f:
            weights_json = json.load(f)
        
        assert weights_json['weights_year'] == 2023
        assert weights_json['grouping'] == 'quintile'
        assert len(weights_json['rows']) == len(weights_df)
        assert 'excluded_share' in weights_json


@pytest.mark.skip(reason="Integration test - requires network and time")
class TestEndToEndCEPipeline:
    """End-to-end test of CE weights pipeline."""
    
    def test_full_pipeline_2023_quintile(self, temp_data_dir, ce_mapping_path, expected_ce_labels):
        """Test complete pipeline: download → validate → extract → save."""
        # Step 1: Download
        ce_file, checksum = download_ce_table(
            year=2023,
            table_type="quintile",
            output_dir=str(temp_data_dir)
        )
        
        # Step 2: Validate
        validation_result = validate_ce_table_structure(
            ce_file,
            expected_table_type="quintile",
            expected_item_labels=expected_ce_labels
        )
        assert validation_result['status'] in ['PASS', 'PASS_WITH_WARNING']
        
        # Step 3: Extract
        weights_df = extract_weights_from_ce_table(
            ce_file,
            table_type="quintile",
            mapping_path=ce_mapping_path
        )
        
        # Step 4: Save
        output_json = temp_data_dir / "curated" / "weights_by_group.json"
        save_weights_to_file(
            weights_df,
            output_json,
            weights_year=2023,
            table_type="quintile",
            metadata={
                "source_file": str(ce_file),
                "source_checksum": checksum
            }
        )
        
        # Final validation
        assert output_json.exists()
        
        # Load and check against schema expectations
        with open(output_json) as f:
            final_weights = json.load(f)
        
        assert final_weights['weights_year'] == 2023
        assert final_weights['grouping'] == 'quintile'
        assert len(final_weights['rows']) == 5 * 8  # 5 groups × 8 categories
        
        print(f"✅ Full pipeline test passed!")
        print(f"  Downloaded: {ce_file.name}")
        print(f"  Checksum: {checksum[:16]}...")
        print(f"  Extracted: {len(weights_df)} weight records")
        print(f"  Saved to: {output_json}")
