#!/usr/bin/env python3
"""Archive and change-track the public NDIS Commission website."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "gov" / "ndis-commission"
SEEDS = ("https://www.ndiscommission.gov.au/lodge-freedom-information-foi-request",)
HOST = "www.ndiscommission.gov.au"
MAX_PAGES = 2000


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href: str | None = None
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href:
            self.links.append(self.href)
            self.href = None


def clean(url: str) -> str:
    url = urldefrag(url)[0]
    return url[:-1] if url.endswith("/") and url != f"https://{HOST}/" else url


def fetch(url: str) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory() as td:
        body = Path(td) / "body"
        headers = Path(td) / "headers"
        cmd = [
            "curl", "--location", "--fail", "--silent", "--show-error",
            "--compressed", "--http1.1", "--connect-timeout", "12",
            "--max-time", "30", "--retry", "2", "--retry-all-errors",
            "--user-agent", "MyNDIS archive monitor (+https://github.com/myNDISwiki/MyNDIS)",
            "--dump-header", str(headers), "--output", str(body), url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        content_types = [
            line.split(":", 1)[1].strip() for line in headers.read_text("iso-8859-1").splitlines()
            if line.lower().startswith("content-type:")
        ]
        return body.read_bytes(), (content_types[-1] if content_types else "")


def destination(url: str, content_type: str) -> Path:
    path = urlparse(url).path.strip("/") or "index"
    if "text/html" in content_type or not Path(path).suffix:
        path += "/current.html"
    return ARCHIVE / path


def main() -> int:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest_path = ARCHIVE / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"items": {}}
    old_items = old.get("items", {})
    queue, seen, items, failures = deque(SEEDS), set(), {}, []
    checked = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    while queue and len(seen) < MAX_PAGES:
        url = clean(queue.popleft())
        parsed = urlparse(url)
        if url in seen or parsed.scheme not in {"http", "https"} or parsed.netloc != HOST:
            continue
        seen.add(url)
        try:
            data, content_type = fetch(url)
        except (OSError, RuntimeError) as error:
            failures.append(f"{url}: {error}")
            if url in old_items:
                items[url] = old_items[url]
            continue
        dest = destination(url, content_type)
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(data).hexdigest()
        if old_items.get(url, {}).get("sha256") != digest or not dest.exists():
            dest.write_bytes(data)
        items[url] = {"sha256": digest, "path": str(dest.relative_to(ROOT)), "content_type": content_type, "canonical_url": url}
        if "text/html" in content_type:
            parser = Links(); parser.feed(data.decode("utf-8", errors="replace"))
            for href in parser.links:
                linked = clean(urljoin(url, href))
                if urlparse(linked).netloc == HOST and linked not in seen:
                    queue.append(linked)

    if failures:
        for url, prior in old_items.items():
            items.setdefault(url, prior)
    manifest = {
        "seeds": list(SEEDS), "checked_at": checked,
        "status": "partial" if failures else "complete", "fetch_failures": failures,
        "items": dict(sorted(items.items())),
        "note": "Same-host public pages are discovered from the seed and retained across partial runs.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"NDIS Commission tracker: {len(items)} retained; {len(failures)} fetch failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
