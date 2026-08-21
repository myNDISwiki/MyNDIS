#!/usr/bin/env python3
"""Discover, archive, and change-track NDIS material on health.gov.au.

Starts from the Department's NDIS legislation hub, follows same-site links that
are either inside the NDIS legislation section or whose URL/link text refers to
NDIS/National Disability Insurance Scheme, and archives HTML pages plus linked
PDF/Word documents. Git history preserves prior versions.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "gov" / "health" / "ndis"
SEED = "https://www.health.gov.au/our-work/ndis-legislation-changes"
HOST = "www.health.gov.au"
MAX_PAGES = 500
UA = "Mozilla/5.0 MyNDIS-Archive/1.0 (+https://github.com/myNDISwiki/MyNDIS)"
DOC_EXT = {".pdf", ".doc", ".docx", ".rtf", ".odt"}
NDIS_RE = re.compile(r"\b(ndis|national disability insurance scheme)\b", re.I)


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []
    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def fetch(url: str) -> tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "en-AU,en;q=0.9", "Cache-Control": "no-cache"})
    with urlopen(req, timeout=45) as r:
        return r.read(), r.headers.get("Content-Type", "")


def clean(url: str) -> str:
    url = urldefrag(url)[0]
    return url[:-1] if url.endswith("/") and url != "https://www.health.gov.au/" else url


def relevant(url: str, text: str = "") -> bool:
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or p.netloc != HOST:
        return False
    if p.path.startswith("/our-work/ndis-legislation-changes"):
        return True
    return bool(NDIS_RE.search(url + " " + text))


def local_path(url: str, content_type: str) -> Path:
    p = urlparse(url)
    path = p.path.strip("/") or "index"
    suffix = Path(path).suffix.lower()
    if "text/html" in content_type or not suffix:
        path = path.rstrip("/") + "/current.html"
    return ARCHIVE / path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest_path = ARCHIVE / "manifest.json"
    old = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {"items": {}}
    old_items = old.get("items", {})
    items: dict[str, dict] = {}
    queue = deque([SEED])
    seen: set[str] = set()
    failures: list[str] = []
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    while queue and len(seen) < MAX_PAGES:
        url = clean(queue.popleft())
        if url in seen or not relevant(url):
            continue
        seen.add(url)
        try:
            data, ctype = fetch(url)
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            failures.append(f"{url}: {e}")
            continue

        dest = local_path(url, ctype)
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = sha(data)
        previous = old_items.get(url, {}).get("sha256")
        if previous != digest or not dest.exists():
            dest.write_bytes(data)
            print(("NEW " if previous is None else "CHANGED ") + url)

        items[url] = {"sha256": digest, "path": str(dest.relative_to(ROOT)), "content_type": ctype}

        if "text/html" in ctype:
            parser = Links()
            parser.feed(data.decode("utf-8", errors="replace"))
            for href, text in parser.links:
                linked = clean(urljoin(url, href))
                if relevant(linked, text):
                    queue.append(linked)

    removed = sorted(set(old_items) - set(items))
    added = sorted(set(items) - set(old_items))
    changed = sorted(u for u in items.keys() & old_items.keys() if items[u]["sha256"] != old_items[u].get("sha256"))

    manifest = {"seed": SEED, "checked_at": checked, "items": dict(sorted(items.items())), "removed_since_previous_run": removed}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")

    log = ARCHIVE / "changelog.md"
    if added or changed or removed or not log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n## {checked}\n\n")
            for label, urls in (("Added", added), ("Changed", changed), ("Removed", removed)):
                if urls:
                    f.write(f"### {label}\n\n")
                    for u in urls:
                        f.write(f"- {u}\n")
                    f.write("\n")

    print(f"Health NDIS tracker: {len(items)} archived; {len(added)} added; {len(changed)} changed; {len(removed)} removed")
    if failures:
        print("Fetch failures:", file=sys.stderr)
        for x in failures:
            print("- " + x, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
