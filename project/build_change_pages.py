#!/usr/bin/env python3
"""Build small, readable change pages beside every archive change ledger."""
from __future__ import annotations

import csv
import html
import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_INLINE_DETAIL = 20000


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def detail_for_row(ledger: Path, row: dict[str, str], manifest: dict) -> str:
    entry = manifest.get(row.get("url", ""), {})
    detail_path = row.get("page_changelog", "")
    if not detail_path and entry.get("directory"):
        detail_path = f"{entry['directory']}/changelog.md"
    if not detail_path:
        return ""
    detail = ROOT / detail_path if detail_path.startswith("archive/") else ledger.parent / detail_path
    if not detail.exists():
        return ""
    content = detail.read_text(encoding="utf-8", errors="replace")
    timestamp = row.get("checked_at") or row.get("timestamp") or ""
    if timestamp:
        sections = re.split(r"(?m)(?=^##\s)", content)
        matching = [section for section in sections if timestamp in section]
        if matching:
            content = matching[-1]
    if len(content) > MAX_INLINE_DETAIL:
        content = content[:MAX_INLINE_DETAIL] + "\n\n[Inline display truncated; open the full changelog.]"
    return content


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
                detail = detail_for_row(ledger, row, manifest)
                if detail:
                    entry = manifest.get(row.get("url", ""), {})
                    detail_path = row.get("page_changelog", "") or (
                        f"{entry['directory']}/changelog.md" if entry.get("directory") else ""
                    )
                    href = os.path.relpath(
                        ROOT / detail_path if detail_path.startswith("archive/") else ledger.parent / detail_path,
                        ledger.parent,
                    )
                    additions = row.get("additions") or ""
                    removals = row.get("removals") or ""
                    label = f"{additions} lines added, {removals} lines removed" if additions or removals else "Show recorded change"
                    value = (
                        f'<details><summary>{esc(label)}</summary>'
                        f'<pre class="detail">{esc(detail)}</pre>'
                        f'<p><a href="{esc(href)}">Open full changelog</a></p></details>'
                    )
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
    generated = max(
        (row.get("checked_at") or row.get("timestamp") or "" for row in rows),
        default="not recorded",
    )
    table_head = "".join(f"<th>{esc(field.replace('_', ' ').title())}</th>" for field in headers)
    out = f'''<!doctype html><meta charset="utf-8"><title>Changes — {esc(label)}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1500px;margin:2rem auto;padding:0 1rem;color:#202124}} table{{border-collapse:collapse;width:100%;font-size:.9rem}} th,td{{border:1px solid #ccd;padding:.55rem;text-align:left;vertical-align:top}} th{{background:#eef2f5;position:sticky;top:0}} tr:nth-child(even){{background:#fafafa}} input{{font:inherit;padding:.6rem;width:min(32rem,100%)}} .meta{{color:#5f6368}} a{{overflow-wrap:anywhere}} .detail{{max-height:32rem;overflow:auto;white-space:pre-wrap;background:#f6f8fa;padding:1rem}}</style>
<h1>Change history</h1><p class="meta">Archive folder: <code>{esc(label)}</code><br>Generated: {esc(generated)}<br>{summary}</p>
<p>This is a readable view of <a href="{esc(ledger.name)}">{esc(ledger.name)}</a>. The ledger and archived source files remain the evidence record.</p>
<label>Filter events <input id="filter" type="search" placeholder="type to filter this history"></label>
<table><thead><tr>{table_head}</tr></thead><tbody id="events">{"".join(body)}</tbody></table>
<script>const i=document.querySelector('#filter');i.addEventListener('input',()=>{{const q=i.value.toLowerCase();document.querySelectorAll('#events tr').forEach(r=>r.hidden=!r.innerText.toLowerCase().includes(q))}})</script>\n'''
    (ledger.parent / "changes.html").write_text(out, encoding="utf-8")


def build_project_page(ledgers: list[Path]) -> None:
    destinations = [ROOT / "project" / "changes.html", ROOT / "project" / "site" / "changes.html"]
    generated = max(
        (
            max(
                (row.get("checked_at") or row.get("timestamp") or "" for row in csv.DictReader(
                    ledger.open(newline="", encoding="utf-8")
                )),
                default="",
            )
            for ledger in ledgers
        ),
        default="not recorded",
    )
    rows = []
    for ledger in sorted(ledgers):
        label = ledger.parent.relative_to(ROOT / "archive").as_posix()
        events = list(csv.DictReader(ledger.open(newline="", encoding="utf-8")))
        latest = max(
            (row.get("checked_at") or row.get("timestamp") or "" for row in events),
            default="not recorded",
        )
        counts = {}
        for row in events:
            event = row.get("event") or row.get("status") or "recorded"
            counts[event] = counts.get(event, 0) + 1
        count_text = ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))
        rows.append((label, latest, count_text, ledger.parent / "changes.html"))
    body = []
    for label, latest, count_text, target in rows:
        href = os.path.relpath(target, ROOT / "project")
        body.append(
            f"<tr><td><a href=\"{esc(href)}\">{esc(label)}</a></td>"
            f"<td>{esc(latest)}</td><td>{esc(count_text)}</td></tr>"
        )
    out = f"""<!doctype html>
<html lang="en-AU">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MyNDIS project changes</title>
  <style>body{{font:16px system-ui,sans-serif;max-width:70rem;margin:2rem auto;padding:0 1rem;color:#202124}} table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ccd;padding:.6rem;text-align:left;vertical-align:top}} th{{background:#eef2f5}} a{{overflow-wrap:anywhere}}</style>
</head>
<body>
  <h1>MyNDIS project changes</h1>
  <p>This overview shows the projects with recorded change events. Open a project to see its detailed history and recorded information.</p>
  <p>Latest recorded event: {esc(generated)}</p>
  <table><thead><tr><th>Project</th><th>Latest change</th><th>Recorded events</th></tr></thead>
  <tbody>{"".join(body)}</tbody></table>
</body>
</html>
"""
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(out, encoding="utf-8")


def main() -> int:
    ledgers = [
        ledger for pattern in ("change-log.csv", "change-ledger.csv")
        for ledger in (ROOT / "archive").rglob(pattern)
        if ledger.parent.name != ".gitkeep"
    ]
    for ledger in ledgers:
        page_for(ledger)
    build_project_page(ledgers)
    print(f"Built {len(ledgers)} archive change pages and project overview pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
