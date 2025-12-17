#!/usr/bin/env python3
"""
Test CE weights pipeline end-to-end with real 2023 data.
Run from project root: python -m scripts.test_ce_pipeline
"""

import sys
import json
from pathlib import Path

from dmi_pipeline.agents.ce_harvester import download_ce_table, validate_ce_table_structure
from dmi_pipeline.agents.ce_weights_builder import extract_weights_from_ce_table,save_weights_to_file

def main():
    print("=" * 60)
    print("CE Weights Pipeline Test - 2023 Quintile Table")
    print("=" * 60)
    
    # Paths
    registry_dir = Path("registry")
    mapping_path = registry_dir / "artifacts" / "ce_table_to_cpi_mapping_v0_1.json"
    policy_path = registry_dir / "policies" / "ce_weights_policy_v0_1.json"
    
    # Load policy for expected labels
    with open(policy_path) as f:
        policy = json.load(f)
    expected_labels = policy['expected_ce_item_labels']
    
    # Step 1: Download
    print("\n[1/4] Downloading 2023 CE quintile table...")
    ce_file, checksum = download_ce_table(
        year=2023,
        table_type="quintile",
        output_dir="data/raw"
    )
    print(f"✓ Downloaded: {ce_file}")
    print(f"  Checksum: {checksum[:16]}...")
    
    # Step 2: Validate
    print("\n[2/4] Validating table structure...")
    validation_result = validate_ce_table_structure(
        ce_file,
        expected_table_type="quintile",
        expected_item_labels=expected_labels
    )
    
    print(f"  Status: {validation_result['status']}")
    for check in validation_result['checks']:
        status_icon = "✓" if check['status'] in ['PASS', 'WARN'] else "✗"
        print(f"  {status_icon} {check['check_id']}: {check['message']}")
    
    if validation_result['status'] == 'FAIL':
        print("\n✗ Validation FAILED. Cannot proceed.")
        return 1
    
    # Step 3: Extract weights
    print("\n[3/4] Extracting weights...")
    weights_df = extract_weights_from_ce_table(
        ce_file,
        table_type="quintile",
        mapping_path=mapping_path
    )
    
    print(f"✓ Extracted {len(weights_df)} weight records")
    print(f"  Groups: {sorted(weights_df['group_id'].unique())}")
    print(f"  Categories: {sorted(weights_df['category_id'].unique())}")
    
    # Validate weights
    print("\n  Weight validation:")
    for group_id in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        group_sum = weights_df[weights_df['group_id'] == group_id]['weight'].sum()
        print(f"    {group_id}: sum = {group_sum:.4f} (target: 1.0000)")
        assert abs(group_sum - 1.0) < 0.001, f"{group_id} weights don't sum to 1.0!"
    
    # Step 4: Save
    print("\n[4/4] Saving weights to JSON...")
    output_path = Path("data/curated/weights_by_group_2023.json")
    save_weights_to_file(
        weights_df,
        output_path,
        weights_year=2023,
        table_type="quintile",
        metadata={
            "source_file": str(ce_file),
            "source_checksum": checksum,
            "created_at": "2025-12-16"
        }
    )
    
    print(f"✓ Saved to: {output_path}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("✓ Pipeline test PASSED!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  • Downloaded CE table: {ce_file.name}")
    print(f"  • Validation: {validation_result['status']}")
    print(f"  • Weights extracted: {len(weights_df)} records")
    print(f"  • Output: {output_path}")
    print("\nWeights by group (Q1 = lowest income, Q5 = highest):")
    print(f"  Groups × Categories: {weights_df['group_id'].nunique()} × {weights_df['category_id'].nunique()} = {len(weights_df)} total")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
