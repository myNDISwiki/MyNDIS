#!/usr/bin/env python3
"""Build master and per-page NDIS archive change histories.

Run after scraper/main.py and before the archive commit. The working tree contains
the newly scraped archive while HEAD contains the previous committed snapshot, so
this script compares the two without storing duplicate page versions.
"""

from __future__ import annotations

import csv
import difflib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = REPO_ROOT / "archive" / "ndis"
MANIFEST_PATH = ARCHIVE_ROOT / "manifest.json"
MASTER_LOG_PATH = ARCHIVE_ROOT / "change-log.csv"

FIELDS = [
    "checked_at",
    "status",
    "resource_type",
    "url",
    "additions",
    "removals",
    "previous_hash",
    "new_hash",
    "page_changelog",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_show(path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def load_json_bytes(data: bytes | None, default: Any) -> Any:
    if data is None:
        return default
    return json.loads(data.decode("utf-8"))


def extract_visible_text(html_bytes: bytes | None) -> list[str]:
    """Return readable content lines, preferring the page's main content."""
    if not html_bytes:
        return []
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    text = root.get_text("\n", strip=True)
    return [line.strip() for line in text.splitlines() if line.strip()]


def resource_type(entry: dict[str, Any]) -> str:
    path = str(entry.get("path", ""))
    return "page" if "/pages/" in f"/{path}" else "document"


def page_changelog_path(entry: dict[str, Any]) -> Path | None:
    path = str(entry.get("path", ""))
    if not path or "/pages/" not in f"/{path}":
        return None
    return (REPO_ROOT / path).parent / "changelog.md"


def make_diff(old_lines: list[str], new_lines: list[str]) -> tuple[int, int, list[str]]:
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
            n=3,
        )
    )
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removals = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return additions, removals, diff


def append_page_history(
    path: Path,
    checked_at: str,
    status: str,
    url: str,
    previous_hash: str,
    new_hash: str,
    additions: int,
    removals: int,
    diff: list[str],
) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        existing = (
            "# Page change history\n\n"
            f"Source: {url}\n\n"
            "This file accumulates the recorded history of this NDIS page. "
            "For language changes, lines beginning `+` were added and lines beginning `-` were removed.\n\n"
        )

    entry = [
        f"## {checked_at} — {status}",
        "",
        f"- Previous SHA-256: `{previous_hash or 'none'}`",
        f"- New SHA-256: `{new_hash or 'none'}`",
        f"- Visible text lines added: {additions}",
        f"- Visible text lines removed: {removals}",
    ]

    if status == "new":
        entry.extend([
            "",
            "Initial capture. The full initial wording is preserved in `index.html`; it is not duplicated here.",
        ])
    elif status == "missing":
        entry.extend([
            "",
            "The page disappeared from the current NDIS sitemap. Its last archived copy remains preserved.",
        ])
    elif diff:
        entry.extend([
            "",
            "### Language change",
            "",
            "```diff",
            *diff,
            "```",
        ])
    else:
        entry.extend([
            "",
            "The page bytes changed, but no visible main-content wording change was detected.",
        ])

    path.write_text(existing + "\n".join(entry) + "\n", encoding="utf-8")


def read_existing_rows() -> list[dict[str, str]]:
    if not MASTER_LOG_PATH.exists():
        return []
    with MASTER_LOG_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    # Convert an early pre-release diff_file column if it ever exists.
    for row in rows:
        row.setdefault("page_changelog", "")
        row.pop("diff_file", None)
    return rows


def write_rows(rows: list[dict[str, str]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    MASTER_LOG_PATH.write_text(output.getvalue(), encoding="utf-8")


def main() -> int:
    current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    previous = load_json_bytes(git_show("archive/ndis/manifest.json"), {"entries": {}})
    current_entries = current.get("entries", {})
    previous_entries = previous.get("entries", {})

    checked_at = now_utc()
    new_rows: list[dict[str, str]] = []

    for url in sorted(set(current_entries) | set(previous_entries)):
        new_entry = current_entries.get(url)
        old_entry = previous_entries.get(url)
        status = ""

        if old_entry is None and new_entry is not None:
            status = "new"
        elif new_entry is None:
            status = "removed-from-manifest"
        elif old_entry is not None:
            old_status = old_entry.get("status", "active")
            new_status = new_entry.get("status", "active")
            if old_status != "missing" and new_status == "missing":
                status = "missing"
            elif old_status == "missing" and new_status == "active":
                status = "restored"
            elif old_entry.get("sha256") != new_entry.get("sha256"):
                status = "changed"

        if not status:
            continue

        entry = new_entry or old_entry or {}
        kind = resource_type(entry)
        additions = 0
        removals = 0
        diff: list[str] = []
        changelog_rel = ""

        if kind == "page":
            current_path = str((new_entry or entry).get("path", ""))
            new_bytes = (REPO_ROOT / current_path).read_bytes() if new_entry and current_path else None
            old_path = str((old_entry or {}).get("path", current_path))
            old_bytes = git_show(old_path) if old_entry and old_path else None

            if status in {"new", "changed", "restored"}:
                additions, removals, diff = make_diff(
                    extract_visible_text(old_bytes),
                    extract_visible_text(new_bytes),
                )

            changelog = page_changelog_path(entry)
            if changelog:
                append_page_history(
                    changelog,
                    checked_at,
                    status,
                    url,
                    str((old_entry or {}).get("sha256", "")),
                    str((new_entry or {}).get("sha256", "")),
                    additions,
                    removals,
                    diff if status != "new" else [],
                )
                changelog_rel = changelog.relative_to(REPO_ROOT).as_posix()

        new_rows.append(
            {
                "checked_at": checked_at,
                "status": status,
                "resource_type": kind,
                "url": url,
                "additions": str(additions),
                "removals": str(removals),
                "previous_hash": str((old_entry or {}).get("sha256", "")),
                "new_hash": str((new_entry or {}).get("sha256", "")),
                "page_changelog": changelog_rel,
            }
        )

    if not new_rows:
        print("No manifest changes to add to change histories")
        return 0

    rows = read_existing_rows()
    rows.extend(new_rows)
    write_rows(rows)
    page_events = sum(bool(row["page_changelog"]) for row in new_rows)
    print(f"Added {len(new_rows)} events to {MASTER_LOG_PATH.relative_to(REPO_ROOT)}")
    print(f"Updated {page_events} per-page changelog entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
