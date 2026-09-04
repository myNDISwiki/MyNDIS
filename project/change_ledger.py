#!/usr/bin/env python3
"""Build cumulative change ledgers for every tracked archive domain.

Scans archive/gov/* trees, compares current files to the previous manifest, and
writes per-domain cumulative CSV ledgers plus a human-readable latest report.
Designed to be called from archival workflows after capture steps complete.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = ROOT / "archive" / "gov"
REPORT_ROOT = ROOT / "archive" / "reports"
STATE_PATH = REPORT_ROOT / "change-ledger-state.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def domain_for(path: Path) -> str:
    rel = path.relative_to(ARCHIVE_ROOT)
    return rel.parts[0] if rel.parts else "unknown"


def snapshot() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not ARCHIVE_ROOT.exists():
        return out
    for p in ARCHIVE_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        out[rel] = {"sha256": sha256(p), "domain": domain_for(p)}
    return out


def append_rows(domain: str, rows: list[dict[str, str]]) -> None:
    domain_dir = REPORT_ROOT / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    ledger = domain_dir / "change-ledger.csv"
    fields = ["timestamp", "domain", "event", "path", "sha256_before", "sha256_after"]
    exists = ledger.exists()
    with ledger.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerows(rows)

    latest = domain_dir / "latest-changes.md"
    with latest.open("w", encoding="utf-8") as f:
        f.write(f"# {domain} latest archive changes\n\n")
        if not rows:
            f.write("No changes detected in this run.\n")
            return
        for event in ("NEW", "MODIFIED", "REMOVED"):
            selected = [r for r in rows if r["event"] == event]
            if selected:
                f.write(f"## {event}\n\n")
                for r in selected:
                    f.write(f"- `{r['path']}`\n")
                f.write("\n")


def main() -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    previous = json.loads(STATE_PATH.read_text("utf-8")) if STATE_PATH.exists() else {}
    current = snapshot()
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    by_domain: dict[str, list[dict[str, str]]] = {}
    all_paths = sorted(set(previous) | set(current))
    for path in all_paths:
        before = previous.get(path)
        after = current.get(path)
        if before is None and after is not None:
            event = "NEW"
            domain = after["domain"]
        elif before is not None and after is None:
            event = "REMOVED"
            domain = before["domain"]
        elif before and after and before.get("sha256") != after.get("sha256"):
            event = "MODIFIED"
            domain = after["domain"]
        else:
            continue
        by_domain.setdefault(domain, []).append({
            "timestamp": ts,
            "domain": domain,
            "event": event,
            "path": path,
            "sha256_before": before.get("sha256", "") if before else "",
            "sha256_after": after.get("sha256", "") if after else "",
        })

    domains = sorted({v["domain"] for v in current.values()} | {v["domain"] for v in previous.values()})
    for domain in domains:
        append_rows(domain, by_domain.get(domain, []))

    STATE_PATH.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"Change ledger: {sum(len(v) for v in by_domain.values())} changes across {len(domains)} domains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
