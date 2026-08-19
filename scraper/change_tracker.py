#!/usr/bin/env python3
"""Create a human-readable NDIS archive change register and exact text diffs.

Run after scraper/main.py and before the archive commit. The current working tree
contains the newly scraped archive while HEAD contains the previous committed
snapshot, so this script can compare the two without duplicating archive data.
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
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = REPO_ROOT / "archive" / "ndis"
MANIFEST_PATH = ARCHIVE_ROOT / "manifest.json"
CHANGE_LOG_PATH = ARCHIVE_ROOT / "change-log.csv"

FIELDS = [
    "checked_at",
    "status",
    "resource_type",
    "url",
    "additions",
    "removals",
    "previous_hash",
    "new_hash",
    "diff_file",
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
    """Return readable content lines, preferring the page's <main> element.

    Scripts, styles and other non-language elements are removed. Repeated blank
    lines are discarded so formatting-only HTML changes do not dominate the diff.
    """
    if not html_bytes:
        return []
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    text = root.get_text("\n", strip=True)
    return [line.strip() for line in text.splitlines() if line.strip()]


def safe_diff_name(url: str) -> str:
    path = urlsplit(url).path.strip("/") or "home"
    cleaned = "__".join(part for part in path.split("/") if part)
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in cleaned)
    return (cleaned or "home")[:180] + ".diff.txt"


def resource_type(entry: dict[str, Any]) -> str:
    path = str(entry.get("path", ""))
    return "page" if "/pages/" in f"/{path}" else "document"


def write_diff(
    checked_at: str,
    url: str,
    old_lines: list[str],
    new_lines: list[str],
) -> tuple[int, int, str]:
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"before: {url}",
            tofile=f"after: {url}",
            lineterm="",
            n=3,
        )
    )
    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removals = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    if not diff:
        return additions, removals, ""

    stamp = checked_at.replace(":", "").replace("-", "")
    diff_path = ARCHIVE_ROOT / "diffs" / stamp / safe_diff_name(url)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"NDIS archived page text change\n"
        f"Checked: {checked_at}\n"
        f"URL: {url}\n"
        f"Lines beginning + were added; lines beginning - were removed.\n\n"
    )
    diff_path.write_text(header + "\n".join(diff) + "\n", encoding="utf-8")
    return additions, removals, diff_path.relative_to(REPO_ROOT).as_posix()


def read_existing_rows() -> list[dict[str, str]]:
    if not CHANGE_LOG_PATH.exists():
        return []
    with CHANGE_LOG_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(rows: list[dict[str, str]]) -> None:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    CHANGE_LOG_PATH.write_text(output.getvalue(), encoding="utf-8")


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
            # The scraper normally retains old manifest entries, but keep this
            # explicit in case the archive format changes later.
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
        diff_file = ""

        if kind == "page" and status in {"new", "changed", "restored"} and new_entry:
            current_path = str(new_entry.get("path", ""))
            new_bytes = (REPO_ROOT / current_path).read_bytes() if current_path else None
            old_path = str(old_entry.get("path", current_path)) if old_entry else current_path
            old_bytes = git_show(old_path) if old_entry else None
            additions, removals, diff_file = write_diff(
                checked_at,
                url,
                extract_visible_text(old_bytes),
                extract_visible_text(new_bytes),
            )

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
                "diff_file": diff_file,
            }
        )

    if not new_rows:
        print("No manifest changes to add to change-log.csv")
        return 0

    rows = read_existing_rows()
    rows.extend(new_rows)
    write_rows(rows)
    print(f"Added {len(new_rows)} change events to {CHANGE_LOG_PATH.relative_to(REPO_ROOT)}")
    print(f"Detailed page-language diffs written for {sum(bool(row['diff_file']) for row in new_rows)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
