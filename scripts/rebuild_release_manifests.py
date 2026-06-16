#!/usr/bin/env python3
"""
Generic rebuilder for releases.json and latest.json from existing raw
dmi_release_*.json artifacts.

This is the targeted retrofit tool used to migrate published manifests to a
new schema/methodology without re-running the full DMI pipeline. It:

  * derives distribution metrics (spread, tilt, most/least pressured groups,
    unemployment) directly from each release's ``dmi_by_group`` so output is
    consistent regardless of which ``summary_metrics`` fields were written at
    compute time;
  * regenerates ``summary`` and ``summary_facts`` via the canonical
    ``build_release_summary`` helper so wording stays in sync with the
    rest of the pipeline;
  * emits the current ``schema_version`` ("2.0.0") and the configured
    ``methodology_version`` (default v0.1.12);
  * supports a period filter (``--periods``) and a ``--dry-run`` mode that
    prints what would change without writing files.

The companion ``backfill_releases.py`` is functionally similar but is used as a
one-shot "rebuild every public release from raw files" tool. This script is
designed to be re-run safely when the schema changes again.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

# Reuse the same summary helper used by the live pipeline so wording does not
# drift between freshly-published releases and retrofitted ones.
from scripts.compute_dmi import build_release_summary


MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

SCHEMA_VERSION = "2.0.0"
DEFAULT_METHODOLOGY_VERSION = "v0.1.12"


def parse_release_id(filename: str) -> Optional[tuple[int, int]]:
    """Parse (year, month) from a ``dmi_release_YYYY-MM.json`` filename."""
    stem = filename.replace("dmi_release_", "").replace(".json", "")
    parts = stem.split("-")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def is_public_release(year: int, month: int) -> bool:
    """Public distribution started with the 2025-12 release."""
    if year < 2025:
        return False
    if year == 2025 and month < 12:
        return False
    return True


def data_through_label(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def derive_metrics(raw_release: dict) -> dict:
    """Derive the v2.0.0 summary metric block from ``dmi_by_group``."""
    dmi_by_group = raw_release["dmi_by_group"]
    dmis = {g["group_id"]: g["dmi"] for g in dmi_by_group}
    max_group = max(dmi_by_group, key=lambda g: g["dmi"])
    min_group = min(dmi_by_group, key=lambda g: g["dmi"])
    return {
        "dmi_median": raw_release["summary_metrics"]["dmi_median"],
        "dmi_stress": raw_release["summary_metrics"]["dmi_stress"],
        "income_pressure_spread": max_group["dmi"] - min_group["dmi"],
        "income_pressure_tilt": dmis["Q1"] - dmis["Q5"],
        "most_pressured_group": max_group["group_id"],
        "least_pressured_group": min_group["group_id"],
        "unemployment": dmi_by_group[0]["slack"],
    }


def build_spec_urls(release_id: str) -> dict:
    base_release_note = f"/data/outputs/releases/{release_id}.html"
    return {
        spec: {
            "csv": f"/data/outputs/dmi-{release_id}-{spec}.csv",
            "parquet": f"/data/outputs/dmi-{release_id}-{spec}.parquet",
            "release_note": base_release_note,
        }
        for spec in ("baseline", "slack_plus", "core")
    }


@dataclass
class RebuildPlan:
    release_id: str
    year: int
    month: int
    raw_path: Path
    metrics: dict
    published_at: str


def discover_releases(
    output_dir: Path,
    requested_periods: Optional[set[str]],
) -> list[RebuildPlan]:
    """Find raw release files to process and validate against ``requested_periods``."""
    plans: list[RebuildPlan] = []
    seen: set[str] = set()

    for path in sorted(output_dir.glob("dmi_release_*.json")):
        # Ignore variant files (e.g. _core, _slack_plus, _u6, _with_ci).
        stem = path.stem.replace("dmi_release_", "")
        if "_" in stem:
            continue
        parsed = parse_release_id(path.name)
        if parsed is None:
            continue
        year, month = parsed
        release_id = f"{year:04d}-{month:02d}"

        if requested_periods is not None and release_id not in requested_periods:
            continue
        if requested_periods is None and not is_public_release(year, month):
            continue

        with path.open() as f:
            raw = json.load(f)
        metrics = derive_metrics(raw)
        published_at = raw["metadata"]["computed_at"].split("T")[0]

        plans.append(RebuildPlan(
            release_id=release_id,
            year=year,
            month=month,
            raw_path=path,
            metrics=metrics,
            published_at=published_at,
        ))
        seen.add(release_id)

    if requested_periods is not None:
        missing = requested_periods - seen
        if missing:
            raise SystemExit(
                f"ERROR: requested periods not found in {output_dir}: "
                f"{sorted(missing)}"
            )

    plans.sort(key=lambda p: p.release_id)
    return plans


def build_release_entry(
    plan: RebuildPlan,
    methodology_version: str,
    prior: Optional[dict],
) -> tuple[dict, dict]:
    """Build a single release entry and its summary_facts."""
    release_id = plan.release_id
    label = data_through_label(plan.year, plan.month)

    base_entry = {
        "release_id": release_id,
        "data_through_label": label,
        "published_at": plan.published_at,
        "status": "superseded",
        "methodology_version": methodology_version,
        "summary": "",
        "summary_facts": {},
        "spec_urls": build_spec_urls(release_id),
        "metrics": dict(plan.metrics),
    }

    summary_facts, summary = build_release_summary(base_entry, prior)
    base_entry["summary"] = summary
    base_entry["summary_facts"] = summary_facts
    return base_entry, summary_facts


def render_diff(old_path: Path, new_obj: dict) -> str:
    """Render a compact, human-readable diff for a manifest file."""
    if not old_path.exists():
        return f"  (new file)\n  schema_version: -> {new_obj['schema_version']}"

    with old_path.open() as f:
        old_obj = json.load(f)

    lines: list[str] = []
    if old_obj.get("schema_version") != new_obj.get("schema_version"):
        lines.append(
            f"  schema_version: {old_obj.get('schema_version')!r} -> "
            f"{new_obj['schema_version']!r}"
        )

    old_by_id = {r["release_id"]: r for r in old_obj.get("releases", [])}
    new_by_id = {r["release_id"]: r for r in new_obj.get("releases", [])}

    for rid in sorted(set(old_by_id) | set(new_by_id)):
        old_r = old_by_id.get(rid)
        new_r = new_by_id.get(rid)
        if old_r is None:
            lines.append(f"  + {rid}: new release")
            continue
        if new_r is None:
            lines.append(f"  - {rid}: removed")
            continue
        # Compare metrics keys
        old_m = old_r.get("metrics", {})
        new_m = new_r.get("metrics", {})
        added = sorted(set(new_m) - set(old_m))
        removed = sorted(set(old_m) - set(new_m))
        changed = []
        for key in sorted(set(old_m) & set(new_m)):
            if old_m[key] != new_m[key]:
                changed.append(key)
        if added or removed or changed or old_r.get("methodology_version") != new_r.get("methodology_version"):
            lines.append(f"  ~ {rid}:")
            if old_r.get("methodology_version") != new_r.get("methodology_version"):
                lines.append(
                    f"      methodology_version: "
                    f"{old_r.get('methodology_version')} -> "
                    f"{new_r.get('methodology_version')}"
                )
            for key in added:
                lines.append(f"      +metrics.{key} = {new_m[key]}")
            for key in removed:
                lines.append(f"      -metrics.{key} (was {old_m[key]})")
            for key in changed:
                lines.append(
                    f"      ~metrics.{key}: {old_m[key]} -> {new_m[key]}"
                )

    return "\n".join(lines) if lines else "  (no changes)"


def assemble_manifests(
    plans: Iterable[RebuildPlan],
    methodology_version: str,
) -> tuple[dict, dict]:
    """Assemble releases.json and latest.json payloads from plans."""
    plan_list = list(plans)
    if not plan_list:
        raise SystemExit("ERROR: no releases to rebuild")

    entries: list[dict] = []
    prior_entry: Optional[dict] = None
    for plan in plan_list:
        entry, _ = build_release_entry(plan, methodology_version, prior_entry)
        entries.append(entry)
        prior_entry = entry

    # Latest is the chronologically newest; mark it current.
    current_entry = entries[-1]
    current_entry["status"] = "current"
    current_release_id = current_entry["release_id"]

    # Sort reverse-chronological for the published manifest.
    releases_sorted = sorted(entries, key=lambda r: r["release_id"], reverse=True)

    generated_at = datetime.utcnow().isoformat() + "Z"
    releases_manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "current_release_id": current_release_id,
        "releases": releases_sorted,
    }
    latest_manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "current_release_id": current_release_id,
        "releases": [current_entry],
    }
    return releases_manifest, latest_manifest


def verify_against_raw(plans: list[RebuildPlan], tol: float = 1e-9) -> None:
    """Verify derived tilt matches each raw release's stored gap value (sanity)."""
    for plan in plans:
        with plan.raw_path.open() as f:
            raw = json.load(f)
        raw_gap = raw["summary_metrics"].get("dmi_income_pressure_gap")
        if raw_gap is None:
            # Newer raw files may omit the legacy field; skip silently.
            continue
        derived_tilt = plan.metrics["income_pressure_tilt"]
        if abs(derived_tilt - raw_gap) > tol:
            raise SystemExit(
                f"ERROR: derived tilt ({derived_tilt}) does not match raw "
                f"dmi_income_pressure_gap ({raw_gap}) for {plan.release_id}"
            )
        if plan.metrics["income_pressure_spread"] <= 0:
            raise SystemExit(
                f"ERROR: income_pressure_spread for {plan.release_id} is "
                f"{plan.metrics['income_pressure_spread']}; expected > 0"
            )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--output-dir",
        default="data/outputs",
        help="Directory containing raw dmi_release_*.json and manifests (default: data/outputs)",
    )
    parser.add_argument(
        "--periods",
        nargs="+",
        metavar="YYYY-MM",
        help="Specific periods to include (default: all public releases, 2025-12+)",
    )
    parser.add_argument(
        "--methodology-version",
        default=DEFAULT_METHODOLOGY_VERSION,
        help=f"Methodology version label to write (default: {DEFAULT_METHODOLOGY_VERSION})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing manifest files",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"ERROR: output directory not found: {output_dir}", file=sys.stderr)
        return 1

    requested = set(args.periods) if args.periods else None

    print(f"Discovering releases in {output_dir}...")
    plans = discover_releases(output_dir, requested)
    if not plans:
        print("No releases matched the requested filter.")
        return 1

    print(f"Selected {len(plans)} release(s):")
    for plan in plans:
        m = plan.metrics
        print(
            f"  {plan.release_id}: spread={m['income_pressure_spread']:.4f}, "
            f"tilt={m['income_pressure_tilt']:+.4f}, "
            f"most={m['most_pressured_group']}, least={m['least_pressured_group']}, "
            f"unemployment={m['unemployment']}"
        )

    verify_against_raw(plans)
    print("Sanity check passed: derived tilt matches raw dmi_income_pressure_gap; spread > 0.")

    releases_manifest, latest_manifest = assemble_manifests(
        plans, args.methodology_version
    )

    releases_path = output_dir / "releases.json"
    latest_path = output_dir / "latest.json"

    print("\nPlanned changes to releases.json:")
    print(render_diff(releases_path, releases_manifest))
    print("\nPlanned changes to latest.json:")
    print(render_diff(latest_path, latest_manifest))

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return 0

    releases_path.write_text(json.dumps(releases_manifest, indent=2))
    latest_path.write_text(json.dumps(latest_manifest, indent=2))
    print(f"\nWrote {releases_path}")
    print(f"Wrote {latest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
