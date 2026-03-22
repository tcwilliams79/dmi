#!/usr/bin/env python3
"""
Update existing DMI output files to use the new key 'dmi_income_pressure_gap' instead of 'dmi_dispersion_q5_q1'.
The new key represents Q1 - Q5, while the old was Q5 - Q1, so we negate the value.
"""

import json
import sys
from pathlib import Path

def update_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    summary_metrics = data.get('summary_metrics', {})
    if 'dmi_dispersion_q5_q1' in summary_metrics:
        old_value = summary_metrics['dmi_dispersion_q5_q1']
        new_value = -old_value  # Q1 - Q5 = -(Q5 - Q1)
        summary_metrics['dmi_income_pressure_gap'] = new_value
        del summary_metrics['dmi_dispersion_q5_q1']
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Updated {filepath}: {old_value:.4f} -> {new_value:.4f}")
        return True
    return False

def main():
    outputs_dir = Path('data/outputs')
    updated_count = 0
    
    for json_file in outputs_dir.rglob('*.json'):
        if update_file(json_file):
            updated_count += 1
    
    print(f"\nUpdated {updated_count} files.")

if __name__ == "__main__":
    main()