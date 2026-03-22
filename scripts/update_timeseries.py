#!/usr/bin/env python3
"""
Append one or more monthly release files into the DMI timeseries.

Usage:
    python -m scripts.update_timeseries 2025-01 2025-02 2025-03

For each period, loads data/outputs/dmi_release_{period}.json and
extracts the 5 quintile observations into the timeseries file.
Duplicates are replaced. The file is sorted by (period, group_id).
"""

import sys
import json
from pathlib import Path

TIMESERIES_PATH = Path("data/outputs/published/dmi_timeseries.json")
RELEASE_DIR = Path("data/outputs")
QUINTILE_ORDER = ["Q1", "Q2", "Q3", "Q4", "Q5"]


def load_timeseries() -> dict:
    with open(TIMESERIES_PATH) as f:
        return json.load(f)


def save_timeseries(ts: dict) -> None:
    TIMESERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TIMESERIES_PATH, "w") as f:
        json.dump(ts, f, indent=2)


def extract_observations(release: dict) -> list[dict]:
    """Extract the 5 quintile observations from a release file."""
    period = release["reference_period"]
    weights_vintage = release.get("parameters", {}).get("weights_year", 2023)
    observations = []
    for group in release["dmi_by_group"]:
        observations.append({
            "period": period,
            "group_id": group["group_id"],
            "dmi": group["dmi"],
            "inflation": group["inflation"],
            "slack": group["slack"],
            "weights_vintage": weights_vintage,
        })
    return observations


def sort_key(obs: dict) -> tuple:
    """Sort by period then quintile order."""
    q_idx = QUINTILE_ORDER.index(obs["group_id"]) if obs["group_id"] in QUINTILE_ORDER else 99
    return (obs["period"], q_idx)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.update_timeseries PERIOD [PERIOD ...]")
        print("  e.g. python -m scripts.update_timeseries 2025-01 2025-02")
        return 1

    periods = sys.argv[1:]
    print(f"Updating timeseries with {len(periods)} period(s): {', '.join(periods)}")

    ts = load_timeseries()
    existing_obs = ts["observations"]

    for period in periods:
        release_path = RELEASE_DIR / f"dmi_release_{period}.json"
        if not release_path.exists():
            print(f"  [SKIP] {period} — release file not found: {release_path}")
            continue

        with open(release_path) as f:
            release = json.load(f)

        new_obs = extract_observations(release)

        # Remove any existing observations for this period (upsert)
        existing_obs = [o for o in existing_obs if o["period"] != period]
        existing_obs.extend(new_obs)
        print(f"  [OK]   {period} — {len(new_obs)} observations added")

    # Sort
    existing_obs.sort(key=sort_key)

    # Update metadata
    all_periods = sorted(set(o["period"] for o in existing_obs))
    ts["observations"] = existing_obs
    ts["observations_count"] = len(existing_obs)
    ts["start_period"] = all_periods[0]
    ts["end_period"] = all_periods[-1]

    save_timeseries(ts)
    print(f"\nTimeseries updated: {ts['observations_count']} observations, "
          f"{ts['start_period']} to {ts['end_period']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
