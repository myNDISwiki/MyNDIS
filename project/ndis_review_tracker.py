#!/usr/bin/env python3
"""Archive the public NDIS Review website and discover same-site pages."""
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
ARCHIVE = ROOT / "archive" / "gov" / "ndis-review"
SEEDS = ("https://www.ndisreview.gov.au/",)
HOST = "www.ndisreview.gov.au"
MAX_PAGES = 2000

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.href = None; self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a": self.href = dict(attrs).get("href")
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href: self.links.append(self.href); self.href = None

def clean(url):
    url = urldefrag(url)[0]
    return url[:-1] if url.endswith("/") and url != f"https://{HOST}/" else url

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
        path = urlparse(url).path.strip("/") or "index"
        if "text/html" in ctype or not Path(path).suffix: path += "/current.html"
        dest = ARCHIVE / path; dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(data).hexdigest()
        if old_items.get(url, {}).get("sha256") != digest or not dest.exists(): dest.write_bytes(data)
        items[url] = {"sha256": digest, "path": str(dest.relative_to(ROOT)), "content_type": ctype, "canonical_url": url}
        if "text/html" in ctype:
            parser = Links(); parser.feed(data.decode("utf-8", errors="replace"))
            queue.extend(clean(urljoin(url, href)) for href in parser.links if urlparse(clean(urljoin(url, href))).netloc == HOST)
    if failures:
        for url, prior in old_items.items(): items.setdefault(url, prior)
    manifest_path.write_text(json.dumps({"seeds": list(SEEDS), "checked_at": checked, "status": "partial" if failures else "complete", "fetch_failures": failures, "items": dict(sorted(items.items()))}, indent=2) + "\n")
    print(f"NDIS Review tracker: {len(items)} retained; {len(failures)} fetch failures")

if __name__ == "__main__": main()
