#!/usr/bin/env python3
"""Build the archive-wide dashboard from tracker outputs."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "archive" / "reports"


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def ledger_latest(path: Path) -> dict[str, int]:
    counts = {"NEW": 0, "MODIFIED": 0, "REMOVED": 0}
    if not path.exists():
        return counts
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    if not rows:
        return counts
    latest = max(row.get("timestamp", "") for row in rows)
    for row in rows:
        if row.get("timestamp") == latest and row.get("event") in counts:
            counts[row["event"]] += 1
    return counts


def main() -> int:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ndis = load_json(ROOT / "archive" / "ndis" / "manifest.json")
    health = load_json(ROOT / "archive" / "gov" / "health" / "ndis" / "manifest.json")
    vic = load_json(REPORTS / "vic-gov" / "statistics.json")
    domains = [
        {
            "id": "ndis", "name": "NDIS website", "status": "active",
            "last_checked": ndis.get("last_run") or ndis.get("checked_at"),
            "tracked_pages": len(ndis.get("pages", ndis.get("items", {}))),
            "registry": "../ndis/manifest.json", "latest": "../ndis/changes/",
            "changes": ledger_latest(REPORTS / "ndis" / "change-ledger.csv"),
        },
        {
            "id": "health", "name": "Health.gov.au NDIS material", "status": health.get("status", "unknown"),
            "last_checked": health.get("checked_at"), "tracked_pages": len(health.get("items", {})),
            "registry": "../gov/health/ndis/manifest.json", "latest": "health/latest-changes.md",
            "changes": ledger_latest(REPORTS / "health" / "change-ledger.csv"),
        },
        {
            "id": "vic-gov", "name": "Victorian Government reforms", "status": vic.get("status", "not run"),
            "last_checked": vic.get("checked_at"), "tracked_pages": vic.get("tracked_pages", 0),
            "registry": "vic-gov/page-registry.csv", "latest": "vic-gov/latest-changes.md",
            "changes": {"NEW": vic.get("new", 0), "MODIFIED": vic.get("modified", 0), "REMOVED": vic.get("removed", 0)},
        },
    ]
    payload = {"generated_at": generated, "domains": domains}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "dashboard.json").write_text(json.dumps(payload, indent=2) + "\n", "utf-8")

    with (REPORTS / "README.md").open("w", encoding="utf-8") as f:
        f.write("# Tracking dashboard\n\n")
        f.write(f"Generated: {generated}\n\n")
        f.write("| Tracker | Status | Last checked | Pages | New | Modified | Removed | Registry | Latest |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---|---|\n")
        for d in domains:
            c = d["changes"]
            f.write(f"| {d['name']} | {d['status']} | {d['last_checked'] or '—'} | {d['tracked_pages']} | {c['NEW']} | {c['MODIFIED']} | {c['REMOVED']} | [open]({d['registry']}) | [open]({d['latest']}) |\n")
        f.write("\nThe Victorian tracker begins at the Thriving Kids page, expands through the Victorian sitemap and relevant links, and automatically registers newly discovered pages. Full response bytes are hashed so even small source changes are retained.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
