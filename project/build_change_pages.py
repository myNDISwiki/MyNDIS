#!/usr/bin/env python3
"""Build small, readable change pages beside every archive change ledger."""
from __future__ import annotations

import csv
import html
import os
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def page_for(ledger: Path) -> None:
    rows = list(csv.DictReader(ledger.open(newline="", encoding="utf-8")))
    manifest = {}
    manifest_path = ledger.parent / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")).get("entries", {})
        except json.JSONDecodeError:
            manifest = {}
    rows.sort(key=lambda row: (row.get("checked_at") or row.get("timestamp") or ""), reverse=True)
    fields = list(rows[0]) if rows else []
    timestamp = "checked_at" if "checked_at" in fields else "timestamp"
    status = "status" if "status" in fields else "event"
    url_field = "url" if "url" in fields else "path"
    counts = {}
    for row in rows:
        key = row.get(status, "unknown") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    summary = " · ".join(f"{esc(key)}: {value}" for key, value in sorted(counts.items())) or "No recorded events"
    headers = [f for f in fields if isinstance(f, str) and f not in {"previous_hash", "new_hash", "sha256_before", "sha256_after"}]
    headers.append("recorded_change")
    body = []
    for row in rows:
        cells = []
        for field in headers:
            if field == "recorded_change":
                entry = manifest.get(row.get("url", ""), {})
                detail_path = row.get("page_changelog", "")
                if not detail_path and entry.get("directory"):
                    detail_path = f"{entry['directory']}/changelog.md"
                if detail_path:
                    detail = ROOT / detail_path if detail_path.startswith("archive/") else ledger.parent / detail_path
                else:
                    detail = None
                if detail and detail.exists():
                    href = os.path.relpath(detail, ledger.parent)
                    additions = row.get("additions") or ""
                    removals = row.get("removals") or ""
                    summary = f"{additions} lines added, {removals} lines removed" if additions or removals else "Open the resource history for the recorded change"
                    value = f'{esc(summary)} · <a href="{esc(href)}">open changelog</a>'
                else:
                    value = "No per-resource history recorded"
                cells.append(f"<td>{value}</td>")
                continue
            value = row.get(field, "")
            if field == url_field and value:
                if value.startswith("http"):
                    value = f'<a href="{esc(value)}">{esc(value)}</a>'
                else:
                    target = Path(value)
                    try:
                        archive_path = ROOT / Path(*target.parts[target.parts.index("archive"):])
                        href = os.path.relpath(archive_path, ledger.parent)
                        value = f'<a href="{esc(href)}">{esc(value)}</a>'
                    except (ValueError, IndexError):
                        value = esc(value)
            else:
                value = esc(value)
            cells.append(f"<td>{value}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    label = ledger.parent.relative_to(ROOT / "archive").as_posix()
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    table_head = "".join(f"<th>{esc(field.replace('_', ' ').title())}</th>" for field in headers)
    out = f'''<!doctype html><meta charset="utf-8"><title>Changes — {esc(label)}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1500px;margin:2rem auto;padding:0 1rem;color:#202124}} table{{border-collapse:collapse;width:100%;font-size:.9rem}} th,td{{border:1px solid #ccd;padding:.55rem;text-align:left;vertical-align:top}} th{{background:#eef2f5;position:sticky;top:0}} tr:nth-child(even){{background:#fafafa}} input{{font:inherit;padding:.6rem;width:min(32rem,100%)}} .meta{{color:#5f6368}} a{{overflow-wrap:anywhere}}</style>
<h1>Change history</h1><p class="meta">Archive folder: <code>{esc(label)}</code><br>Generated: {esc(generated)}<br>{summary}</p>
<p>This is a readable view of <a href="{esc(ledger.name)}">{esc(ledger.name)}</a>. The ledger and archived source files remain the evidence record.</p>
<label>Filter events <input id="filter" type="search" placeholder="type to filter this history"></label>
<table><thead><tr>{table_head}</tr></thead><tbody id="events">{"".join(body)}</tbody></table>
<script>const i=document.querySelector('#filter');i.addEventListener('input',()=>{{const q=i.value.toLowerCase();document.querySelectorAll('#events tr').forEach(r=>r.hidden=!r.innerText.toLowerCase().includes(q))}})</script>\n'''
    (ledger.parent / "changes.html").write_text(out, encoding="utf-8")


def build_project_page(ledgers: list[Path]) -> None:
    site = ROOT / "project" / "site"
    site.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    links = []
    for ledger in sorted(ledgers):
        label = ledger.parent.relative_to(ROOT / "archive").as_posix()
        href = os.path.relpath(ledger.parent / "changes.html", site)
        links.append(f'<li><a href="{esc(href)}">{esc(label)}</a></li>')
    out = f"""<!doctype html>
<html lang="en-AU">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MyNDIS change histories</title>
  <style>body{{font:16px system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;color:#202124}} a{{overflow-wrap:anywhere}}</style>
</head>
<body>
  <h1>MyNDIS change histories</h1>
  <p>Generated: {esc(generated)}</p>
  <ul>{"".join(links)}</ul>
</body>
</html>
"""
    (site / "changes.html").write_text(out, encoding="utf-8")


def main() -> int:
    ledgers = [
        ledger for pattern in ("change-log.csv", "change-ledger.csv")
        for ledger in (ROOT / "archive").rglob(pattern)
        if ledger.parent.name != ".gitkeep"
    ]
    for ledger in ledgers:
        page_for(ledger)
    build_project_page(ledgers)
    print(f"Built {len(ledgers)} archive change pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
