#!/usr/bin/env python3
"""Build the archive-wide dashboard from tracker outputs."""
from __future__ import annotations

import csv
import html
import json
import os
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
    # Keep each source folder locally browsable, alongside its raw ledger.
    import build_change_pages
    build_change_pages.main()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ndis = load_json(ROOT / "archive" / "ndis" / "manifest.json")
    health = load_json(ROOT / "archive" / "gov" / "health" / "ndis" / "manifest.json")
    vic = load_json(REPORTS / "vic-gov" / "statistics.json")
    dataresearch = load_json(ROOT / "archive" / "dataresearch" / "manifest.json")
    dataresearch_run = load_json(ROOT / "archive" / "dataresearch" / "latest-run.json")
    issues = []
    if dataresearch_run.get("errors"):
        issues.append(
            {
                "project": "NDIS data and research",
                "severity": "warning",
                "message": f"{len(dataresearch_run['errors'])} capture error(s); successful captures were retained.",
                "href": "../archive/dataresearch/latest-run.json",
            }
        )
    if dataresearch_run.get("robots_exclusions"):
        issues.append(
            {
                "project": "NDIS data and research",
                "severity": "info",
                "message": f"{len(dataresearch_run['robots_exclusions'])} resource(s) excluded by robots.txt.",
                "href": "../archive/dataresearch/latest-run.json",
            }
        )
    domains = [
        {
            "id": "dataresearch", "name": "NDIS data and research", "status": dataresearch.get("status", "not run"),
            "last_checked": dataresearch.get("checked_at"),
            "tracked_pages": sum(e.get("kind") == "page" for e in dataresearch.get("entries", {}).values()),
            "registry": "../dataresearch/manifest.json", "latest": "../dataresearch/latest-run.json",
            "changes": {"NEW": sum(e["event"] == "new" for e in dataresearch_run.get("events", [])), "MODIFIED": sum(e["event"] == "changed" for e in dataresearch_run.get("events", [])), "REMOVED": 0},
        },
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
    known_ids = {domain["id"] for domain in domains}
    for ledger in sorted((ROOT / "archive").rglob("change-ledger.csv")):
        project_id = ledger.parent.relative_to(ROOT / "archive").as_posix()
        if project_id in known_ids:
            continue
        rows = list(csv.DictReader(ledger.open(newline="", encoding="utf-8")))
        latest = max(
            (row.get("checked_at") or row.get("timestamp") or "" for row in rows),
            default=None,
        )
        changes = {"NEW": 0, "MODIFIED": 0, "REMOVED": 0}
        for row in rows:
            event = (row.get("event") or row.get("status") or "").upper()
            if event in changes:
                changes[event] += 1
        domains.append(
            {
                "id": project_id,
                "name": project_id.replace("-", " ").replace("/", " / ").title(),
                "status": "recorded changes",
                "last_checked": latest,
                "tracked_pages": 0,
                "registry": os.path.relpath(ledger, REPORTS),
                "latest": os.path.relpath(ledger.parent / "changes.html", REPORTS),
                "changes": changes,
            }
        )
    for domain in domains:
        if str(domain["status"]).lower() in {"partial", "failed", "failure", "error"}:
            detail_href = (
                "../archive/dataresearch/latest-run.json"
                if domain["id"] == "dataresearch"
                else f"../archive/reports/{domain['id']}/changes.html"
            )
            issues.append(
                {
                    "project": domain["name"],
                    "severity": "warning",
                    "message": f"Tracker status is {domain['status']}.",
                    "href": detail_href,
                }
            )
    payload = {"generated_at": generated, "domains": domains, "issues": issues}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "dashboard.json").write_text(json.dumps(payload, indent=2) + "\n", "utf-8")

    cards = []
    for domain in domains:
        changes = domain["changes"]
        history = {
            "dataresearch": "../archive/dataresearch/changes.html",
            "ndis": "../archive/ndis/changes.html",
            "health": "../archive/reports/health/changes.html",
            "vic-gov": "../archive/reports/vic-gov/changes.html",
        }.get(domain["id"], f"../archive/reports/{domain['id']}/changes.html")
        cards.append(
            f"""<article class="card">
  <h2>{html.escape(domain["name"])}</h2>
  <p class="status">{html.escape(str(domain["status"]))}</p>
  <dl>
    <dt>Last checked</dt><dd>{html.escape(str(domain["last_checked"] or "—"))}</dd>
    <dt>Tracked pages</dt><dd>{domain["tracked_pages"]}</dd>
    <dt>Changes</dt><dd>New {changes["NEW"]} · Modified {changes["MODIFIED"]} · Removed {changes["REMOVED"]}</dd>
  </dl>
  <a class="button" href="{history}">View detailed changes</a>
</article>"""
        )
    issue_items = "".join(
        f'<li><strong>{html.escape(issue["project"])}</strong> '
        f'<span class="severity {issue["severity"]}">{html.escape(issue["severity"])}</span> — '
        f'{html.escape(issue["message"])} <a href="{html.escape(issue["href"], quote=True)}">View details</a></li>'
        for issue in issues
    ) or "<li>No known failures or attention items recorded.</li>"
    (ROOT / "project" / "dashboard.html").write_text(
        f"""<!doctype html>
<html lang="en-AU">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MyNDIS tracking dashboard</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font: 16px system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #202124; background: #f7f9fb; }}
    h1 {{ margin-bottom: .25rem; }}
    .meta {{ color: #5f6368; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
    .card {{ background: white; border: 1px solid #d9e0e7; border-radius: .6rem; padding: 1rem; box-shadow: 0 1px 2px #0001; }}
    .card h2 {{ margin-top: 0; font-size: 1.15rem; }}
    .status {{ display: inline-block; padding: .2rem .55rem; border-radius: 999px; background: #e8f0fe; }}
    dl {{ display: grid; grid-template-columns: max-content 1fr; gap: .4rem .8rem; }}
    dt {{ color: #5f6368; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
    .button {{ display: inline-block; margin-top: .7rem; padding: .5rem .75rem; border-radius: .35rem; background: #1769aa; color: white; text-decoration: none; }}
    .button:hover {{ background: #0d4f82; }}
    .issues {{ background: #fff8e1; border: 1px solid #e6c65c; border-radius: .6rem; padding: 1rem 1rem 1rem 2.5rem; }}
    .severity {{ border-radius: 999px; padding: .15rem .45rem; font-size: .8rem; text-transform: uppercase; }}
    .severity.warning {{ background: #fce8e6; color: #a50e0e; }}
    .severity.info {{ background: #e8f0fe; color: #174ea6; }}
  </style>
</head>
<body>
  <h1>MyNDIS tracking dashboard</h1>
  <p class="meta">Generated: {html.escape(generated)} · <a href="changes.html">Overall change history</a></p>
  <h2>Issues needing attention</h2>
  <ul class="issues">{issue_items}</ul>
  <h2>Trackers</h2>
  <div class="grid">{"".join(cards)}</div>
</body>
</html>
""",
        encoding="utf-8",
    )

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
