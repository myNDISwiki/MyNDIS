#!/usr/bin/env python3
"""Discover, archive, and change-track NDIS material on health.gov.au.

The tracker first attempts direct retrieval from Health.gov.au. GitHub-hosted
Azure runners are currently receiving zero-byte timeouts from Health's edge, so
when direct retrieval fails it falls back to Jina Reader. Canonical Health.gov.au
URLs remain the source identifiers. Metadata records which retrieval path was
used so proxy-derived captures are never mistaken for direct raw HTML.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urldefrag

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "gov" / "health" / "ndis"
SEED = "https://www.health.gov.au/our-work/ndis-legislation-changes"
HOST = "www.health.gov.au"
MAX_PAGES = 500
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)
NDIS_RE = re.compile(r"\b(ndis|national disability insurance scheme)\b", re.I)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\)")
RAW_URL_RE = re.compile(r"https?://www\.health\.gov\.au/[^\s)>\]}"']+")


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


def curl_fetch(url: str, *, timeout: int, retries: int = 0) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory() as td:
        body = Path(td) / "body"
        headers = Path(td) / "headers"
        cmd = [
            "curl", "--location", "--fail", "--silent", "--show-error",
            "--compressed", "--http1.1",
            "--connect-timeout", "12", "--max-time", str(timeout),
            "--user-agent", UA,
            "--header", "Accept: text/html,application/xhtml+xml,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,*/*;q=0.8",
            "--header", "Accept-Language: en-AU,en;q=0.9",
            "--dump-header", str(headers), "--output", str(body),
        ]
        if retries:
            cmd += ["--retry", str(retries), "--retry-all-errors", "--retry-delay", "3"]
        cmd.append(url)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or f"curl exit {proc.returncode}").strip())
        data = body.read_bytes()
        header_text = headers.read_text("iso-8859-1", errors="replace")
        content_types = re.findall(r"(?im)^content-type:\s*([^\r\n]+)", header_text)
        return data, (content_types[-1].strip() if content_types else "")


def fetch(url: str) -> tuple[bytes, str, str]:
    """Return bytes, content type, and retrieval method."""
    try:
        data, ctype = curl_fetch(url, timeout=20, retries=0)
        return data, ctype, "direct"
    except RuntimeError as direct_error:
        print(f"Direct Health fetch failed; using fallback for {url}: {direct_error}", file=sys.stderr)

    # Jina Reader fetches the canonical public URL from outside GitHub's Azure
    # runner network and returns a text/markdown rendering suitable for hashing,
    # link discovery, and change tracking. It is explicitly labelled as fallback.
    fallback_url = "https://r.jina.ai/http://" + url.removeprefix("https://")
    data, _ = curl_fetch(fallback_url, timeout=60, retries=2)
    return data, "text/markdown; charset=utf-8", "jina-reader-fallback"


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


def local_path(url: str, content_type: str, method: str) -> Path:
    p = urlparse(url)
    path = p.path.strip("/") or "index"
    suffix = Path(path).suffix.lower()
    if method != "direct":
        return ARCHIVE / path.rstrip("/") / "current.md"
    if "text/html" in content_type or not suffix:
        path = path.rstrip("/") + "/current.html"
    return ARCHIVE / path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def discovered_links(url: str, data: bytes, ctype: str, method: str) -> list[str]:
    text = data.decode("utf-8", errors="replace")
    found: list[str] = []
    if method == "direct" and "text/html" in ctype:
        parser = Links()
        parser.feed(text)
        for href, label in parser.links:
            linked = clean(urljoin(url, href))
            if relevant(linked, label):
                found.append(linked)
    else:
        candidates = MD_LINK_RE.findall(text) + RAW_URL_RE.findall(text)
        for candidate in candidates:
            linked = clean(candidate.rstrip(".,;"))
            if relevant(linked):
                found.append(linked)
    return found


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
            data, ctype, method = fetch(url)
        except (RuntimeError, OSError) as e:
            failures.append(f"{url}: {e}")
            continue

        dest = local_path(url, ctype, method)
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = sha(data)
        previous = old_items.get(url, {}).get("sha256")
        if previous != digest or not dest.exists():
            dest.write_bytes(data)
            print(("NEW " if previous is None else "CHANGED ") + url + f" [{method}]")

        items[url] = {
            "sha256": digest,
            "path": str(dest.relative_to(ROOT)),
            "content_type": ctype,
            "canonical_url": url,
            "retrieval_method": method,
            "retrieval_note": (
                "Direct capture from health.gov.au" if method == "direct" else
                "Fallback text rendering via Jina Reader because health.gov.au timed out from GitHub-hosted runner"
            ),
        }

        for linked in discovered_links(url, data, ctype, method):
            if linked not in seen:
                queue.append(linked)

    removed = sorted(set(old_items) - set(items))
    added = sorted(set(items) - set(old_items))
    changed = sorted(u for u in items.keys() & old_items.keys() if items[u]["sha256"] != old_items[u].get("sha256"))

    manifest = {
        "seed": SEED,
        "checked_at": checked,
        "items": dict(sorted(items.items())),
        "removed_since_previous_run": removed,
        "note": "Canonical sources are health.gov.au. retrieval_method identifies direct vs fallback captures.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")

    log = ARCHIVE / "changelog.md"
    if added or changed or removed or not log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n## {checked}\n\n")
            for label, urls in (("Added", added), ("Changed", changed), ("Removed", removed)):
                if urls:
                    f.write(f"### {label}\n\n")
                    for u in urls:
                        method = items.get(u, old_items.get(u, {})).get("retrieval_method", "unknown")
                        f.write(f"- {u} — `{method}`\n")
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
