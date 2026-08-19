#!/usr/bin/env python3
"""Track configured Australian government webpages under archive/gov.

Each source keeps a current raw HTML snapshot plus an append-only human-readable
change log. Git history preserves each prior snapshot version. Additional sources
can be added to project/gov-sources.json without changing this script.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "project" / "gov-sources.json"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36 MyNDIS-Archive/1.0"
)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "template"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "template"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def visible_lines(data: bytes) -> list[str]:
    parser = VisibleTextParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    return parser.parts


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=45) as response:
        return response.read()


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def append_changelog(
    path: Path,
    *,
    title: str,
    url: str,
    checked_at: str,
    old_hash: str,
    new_hash: str,
    old_data: bytes | None,
    new_data: bytes,
) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        existing = (
            f"# Change history — {title}\n\n"
            f"Source: {url}\n\n"
            "Git history preserves each raw HTML snapshot. This file records visible-text changes.\n\n"
        )

    if old_data is None:
        body = [
            f"## {checked_at} — initial capture",
            "",
            f"- SHA-256: `{new_hash}`",
            "- Full page saved as `current.html`.",
        ]
    else:
        diff = list(
            difflib.unified_diff(
                visible_lines(old_data),
                visible_lines(new_data),
                fromfile="before",
                tofile="after",
                lineterm="",
                n=3,
            )
        )
        additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removals = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        body = [
            f"## {checked_at} — changed",
            "",
            f"- Previous SHA-256: `{old_hash}`",
            f"- New SHA-256: `{new_hash}`",
            f"- Visible text lines added: {additions}",
            f"- Visible text lines removed: {removals}",
        ]
        if diff:
            body.extend(["", "```diff", *diff, "```"])
        else:
            body.extend(["", "Page bytes changed, but no visible-text change was detected."])

    path.write_text(existing + "\n".join(body) + "\n", encoding="utf-8")


def process_source(source: dict, checked_at: str) -> bool:
    source_id = source["id"]
    title = source["title"]
    url = source["url"]
    root = REPO_ROOT / source["archive_path"]
    snapshot_path = root / "current.html"
    metadata_path = root / "metadata.json"
    changelog_path = root / "changelog.md"

    print(f"Fetching {source_id}: {url}")
    data = fetch(url)
    digest = sha256(data)

    metadata = load_json(metadata_path, {})
    old_hash = str(metadata.get("sha256", ""))
    old_data = snapshot_path.read_bytes() if snapshot_path.exists() else None

    if old_hash == digest and old_data is not None:
        print(f"UNCHANGED {source_id}")
        return False

    root.mkdir(parents=True, exist_ok=True)
    append_changelog(
        changelog_path,
        title=title,
        url=url,
        checked_at=checked_at,
        old_hash=old_hash,
        new_hash=digest,
        old_data=old_data,
        new_data=data,
    )
    snapshot_path.write_bytes(data)
    write_json(
        metadata_path,
        {
            "id": source_id,
            "title": title,
            "url": url,
            "checked_at": checked_at,
            "sha256": digest,
        },
    )
    print(f"UPDATED {source_id}")
    return True


def main() -> int:
    config = load_json(CONFIG_PATH, None)
    if not isinstance(config, dict) or not isinstance(config.get("sources"), list):
        raise RuntimeError(f"Invalid config: {CONFIG_PATH}")

    checked_at = now_utc()
    failures: list[str] = []
    changed = 0

    for source in config["sources"]:
        try:
            changed += int(process_source(source, checked_at))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            source_id = str(source.get("id", "unknown"))
            failures.append(f"{source_id}: {exc}")
            print(f"ERROR {source_id}: {exc}", file=sys.stderr)

    print(f"Government tracker complete: {changed} source(s) changed")
    if failures:
        print("Failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
