#!/usr/bin/env python3
"""Crawl and archive the public Engage NDIS site."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "gov" / "engage-ndis"
SEEDS = ("https://engage.ndis.gov.au/", "https://engage.ndis.gov.au/projects")
HOST = "engage.ndis.gov.au"
MAX_PAGES = 2000


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.href = None; self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a": self.href = dict(attrs).get("href")
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href: self.links.append(self.href); self.href = None


def clean(url):
    return urldefrag(url)[0].rstrip("/") or f"https://{HOST}"


def fetch(url):
    with tempfile.TemporaryDirectory() as td:
        body, headers = Path(td) / "body", Path(td) / "headers"
        result = subprocess.run([
            "curl", "--location", "--fail", "--silent", "--show-error", "--compressed",
            "--http1.1", "--connect-timeout", "12", "--max-time", "30", "--retry", "2",
            "--retry-all-errors", "--user-agent", "MyNDIS archive monitor",
            "--dump-header", str(headers), "--output", str(body), url,
        ], capture_output=True, text=True)
        if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip())
        types = [x.split(":", 1)[1].strip() for x in headers.read_text("iso-8859-1").splitlines() if x.lower().startswith("content-type:")]
        return body.read_bytes(), (types[-1] if types else "")


def main():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest_path = ARCHIVE / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"items": {}}
    old_items, queue, seen, items, failures = old.get("items", {}), deque(SEEDS), set(), {}, []
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    while queue and len(seen) < MAX_PAGES:
        url = clean(queue.popleft())
        if url in seen or urlparse(url).netloc != HOST: continue
        seen.add(url)
        try: data, ctype = fetch(url)
        except (OSError, RuntimeError) as error:
            failures.append(f"{url}: {error}"); items.setdefault(url, old_items.get(url, {})); continue
        path = urlparse(url).path.strip("/") or "home"
        if "text/html" in ctype or not Path(path).suffix: path += "/index.html"
        dest = ARCHIVE / "pages" / path; dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(data).hexdigest()
        if old_items.get(url, {}).get("sha256") != digest or not dest.exists(): dest.write_bytes(data)
        items[url] = {"sha256": digest, "path": str(dest.relative_to(ROOT)), "content_type": ctype, "canonical_url": url}
        if "text/html" in ctype:
            parser = Links(); parser.feed(data.decode("utf-8", errors="replace"))
            queue.extend(clean(urljoin(url, href)) for href in parser.links if urlparse(clean(urljoin(url, href))).netloc == HOST)
    if failures:
        for url, prior in old_items.items(): items.setdefault(url, prior)
    manifest = {"seeds": list(SEEDS), "checked_at": checked, "status": "partial" if failures else "complete", "fetch_failures": failures, "items": dict(sorted(items.items()))}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    rows = [f'<li><a href="{u}">{urlparse(u).path or "/"}</a></li>' for u in sorted(items)]
    (ARCHIVE / "index.html").write_text("<!doctype html><meta charset='utf-8'><title>Engage NDIS archive</title><h1>Engage NDIS archive</h1><p>Tracked pages: %d. Checked: %s</p><ul>%s</ul>" % (len(items), checked, "".join(rows)), encoding="utf-8")
    print(f"Engage NDIS tracker: {len(items)} retained; {len(failures)} fetch failures")


if __name__ == "__main__": main()
