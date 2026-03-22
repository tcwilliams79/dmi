#!/usr/bin/env python3
"""
One-time backfill: generate missing monthly DMI releases (2024-12 through 2025-11).

Reuses compute_dmi_for_period and save_dmi_output from compute_dmi.py,
loading the correct staging files for each period.
"""

import sys
import json
from pathlib import Path

import pandas as pd

from scripts.compute_dmi import (
    load_weights,
    load_cpi_data,
    load_slack_data,
    compute_dmi_for_period,
    save_dmi_output,
)

# Missing periods and which staging file pair to use
MISSING_PERIODS = [
    # (period, cpi_file_suffix, slack_file_suffix)
    ("2024-12", "2023_2024", "2023_2024"),
    ("2025-01", "2025_2026", "2025_2026"),
    ("2025-02", "2025_2026", "2025_2026"),
    ("2025-03", "2025_2026", "2025_2026"),
    ("2025-04", "2025_2026", "2025_2026"),
    ("2025-05", "2025_2026", "2025_2026"),
    ("2025-06", "2025_2026", "2025_2026"),
    ("2025-07", "2025_2026", "2025_2026"),
    ("2025-08", "2025_2026", "2025_2026"),
    ("2025-11", "2025_2026", "2025_2026"),
]


def main():
    print("=" * 80)
    print("Generate Missing DMI Releases")
    print("=" * 80)

    weights_path = Path("data/curated/weights_by_group_2023.json")
    weights_df = load_weights(weights_path)
    print(f"Loaded weights: {len(weights_df)} records")

    # Cache loaded staging files to avoid re-reading
    cpi_cache: dict[str, pd.DataFrame] = {}
    slack_cache: dict[str, pd.DataFrame] = {}

    generated = 0
    skipped = 0

    for period, cpi_suffix, slack_suffix in MISSING_PERIODS:
        output_path = Path(f"data/outputs/dmi_release_{period}.json")
        if output_path.exists():
            print(f"\n[SKIP] {period} — release file already exists")
            skipped += 1
            continue

        # Load CPI data (with caching)
        if cpi_suffix not in cpi_cache:
            cpi_path = Path(f"data/staging/cpi_levels_{cpi_suffix}.json")
            cpi_cache[cpi_suffix] = load_cpi_data(cpi_path)
        cpi_df = cpi_cache[cpi_suffix]

        # Load slack data (with caching)
        if slack_suffix not in slack_cache:
            slack_path = Path(f"data/staging/slack_u3_{slack_suffix}.json")
            slack_cache[slack_suffix] = load_slack_data(slack_path)
        slack_df = slack_cache[slack_suffix]

        # Check that the period actually exists in the data
        cpi_periods = set(cpi_df["period"].unique())
        slack_periods = set(slack_df["period"].unique())
        if period not in cpi_periods:
            print(f"\n[SKIP] {period} — CPI data not available in staging/{cpi_suffix}")
            skipped += 1
            continue
        if period not in slack_periods:
            print(f"\n[SKIP] {period} — slack data not available in staging/{slack_suffix}")
            skipped += 1
            continue

        print(f"\n{'=' * 80}")
        try:
            results = compute_dmi_for_period(
                cpi_df=cpi_df,
                weights_df=weights_df,
                slack_df=slack_df,
                reference_period=period,
            )
            save_dmi_output(results, output_path)
            generated += 1
        except Exception as e:
            print(f"  ERROR computing {period}: {e}")
            skipped += 1

    print(f"\n{'=' * 80}")
    print(f"Done. Generated: {generated}, Skipped: {skipped}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
