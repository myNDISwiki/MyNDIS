#!/usr/bin/env python3
"""Discover and byte-track Victorian Government pages relevant to NDIS reform."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "archive" / "gov" / "vic-gov"
REPORTS = ROOT / "archive" / "reports" / "vic-gov"
SEED = "https://www.vic.gov.au/thriving-kids"
HOSTS = {"www.vic.gov.au", "vic.gov.au"}
MAX_PAGES = 250
DELAY = 2.0
UA = "MyNDISArchiveBot/1.0 (+https://github.com/myNDISwiki/MyNDIS)"
TERMS = (
    "thriving kids", "foundational support", "ndis", "national disability insurance",
    "disability reform", "developmental support", "developmental delay",
    "early childhood support", "early childhood intervention", "navigation partner",
    "navigator partner", "support needs", "autism support",
)
URL_HINTS = (
    "thriving-kids", "foundational-support", "ndis", "disability-reform",
    "developmental-support", "developmental-delay", "early-childhood",
    "navigation-partner", "navigator-partner",
)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.links: list[tuple[str, str]] = []
        self._in_title = False
        self._href: str | None = None
        self._anchor: list[str] = []
        self.text: list[str] = []
        self._hidden = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._hidden += 1
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._anchor = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "template"} and self._hidden:
            self._hidden -= 1
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._anchor)))
            self._href = None

    def handle_data(self, data):
        if self._hidden:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        self.text.append(value)
        if self._in_title:
            self.title += value
        if self._href is not None:
            self._anchor.append(value)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical(raw: str, base: str = SEED) -> str | None:
    p = urlparse(urljoin(base, raw))
    if p.scheme not in {"http", "https"} or p.netloc.lower() not in HOSTS:
        return None
    path = re.sub(r"/+", "/", p.path).rstrip("/") or "/"
    return urlunparse(("https", "www.vic.gov.au", path, "", "", ""))


def relevant(value: str) -> bool:
    value = value.lower().replace("-", " ").replace("_", " ")
    return any(term in value for term in TERMS) or any(hint in value.replace(" ", "-") for hint in URL_HINTS)


def get(url: str) -> tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
    with urlopen(req, timeout=60) as response:
        return response.read(), response.headers.get("Content-Type", "")


def sitemap_candidates() -> set[str]:
    candidates = {SEED}
    data, _ = get("https://www.vic.gov.au/sitemap.xml")
    root = ET.fromstring(data)
    sitemap_urls = [node.text for node in root.findall(".//{*}loc") if node.text]
    for sitemap in sitemap_urls:
        try:
            time.sleep(DELAY)
            body, _ = get(sitemap)
            child = ET.fromstring(body)
        except Exception as exc:
            print(f"Sitemap discovery failed for {sitemap}: {exc}")
            continue
        for node in child.findall(".//{*}loc"):
            if node.text and relevant(node.text):
                url = canonical(node.text)
                if url:
                    candidates.add(url)
    return candidates


def page_path(url: str) -> Path:
    path = urlparse(url).path.strip("/") or "home"
    return ARCHIVE / "pages" / path / "current.html"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_registry() -> dict[str, dict[str, str]]:
    path = REPORTS / "page-registry.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {row["url"]: row for row in csv.DictReader(f)}


def write_outputs(items: dict[str, dict[str, str]], old: dict[str, dict[str, str]], checked: str, failures: list[str]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    fields = ["url", "title", "archive_path", "sha256", "first_seen", "last_checked", "status", "discovered_from"]
    with (REPORTS / "page-registry.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items[url] for url in sorted(items))

    changes = []
    for url in sorted(set(old) | set(items)):
        before, after = old.get(url), items.get(url)
        if before is None:
            event = "NEW"
        elif after is None:
            event = "REMOVED"
        elif before.get("sha256") != after.get("sha256"):
            event = "MODIFIED"
        else:
            continue
        changes.append({"timestamp": checked, "event": event, "url": url,
                        "sha256_before": before.get("sha256", "") if before else "",
                        "sha256_after": after.get("sha256", "") if after else ""})

    ledger = REPORTS / "change-ledger.csv"
    ledger_fields = ["timestamp", "event", "url", "sha256_before", "sha256_after"]
    exists = ledger.exists()
    with ledger.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ledger_fields)
        if not exists:
            writer.writeheader()
        writer.writerows(changes)

    with (REPORTS / "latest-changes.md").open("w", encoding="utf-8") as f:
        f.write("# Victorian Government latest changes\n\n")
        f.write(f"Checked: {checked}\n\n")
        if not changes:
            f.write("No page changes detected in this run.\n")
        for event in ("NEW", "MODIFIED", "REMOVED"):
            selected = [row for row in changes if row["event"] == event]
            if selected:
                f.write(f"## {event}\n\n")
                for row in selected:
                    f.write(f"- {row['url']}\n")
                f.write("\n")
        if failures:
            f.write("## Fetch failures\n\n")
            for failure in failures:
                f.write(f"- {failure}\n")

    stats = {
        "domain": "vic.gov.au", "seed": SEED, "checked_at": checked,
        "status": "partial" if failures else "complete", "tracked_pages": len(items),
        "new": sum(x["event"] == "NEW" for x in changes),
        "modified": sum(x["event"] == "MODIFIED" for x in changes),
        "removed": sum(x["event"] == "REMOVED" for x in changes),
        "fetch_failures": len(failures),
    }
    (REPORTS / "statistics.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    checked = now()
    old = read_registry()
    queue = deque(sorted(sitemap_candidates() | set(old)))
    queued = set(queue)
    items: dict[str, dict[str, str]] = {}
    failures: list[str] = []

    while queue and len(items) < MAX_PAGES:
        url = queue.popleft()
        try:
            time.sleep(DELAY)
            data, content_type = get(url)
            if "text/html" not in content_type:
                continue
            parser = PageParser()
            parser.feed(data.decode("utf-8", errors="replace"))
            full_text = " ".join(parser.text)
            if url != SEED and not relevant(url + " " + parser.title + " " + full_text):
                continue
            dest = page_path(url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            sha = digest(data)
            if not dest.exists() or old.get(url, {}).get("sha256") != sha:
                dest.write_bytes(data)
            prior = old.get(url, {})
            items[url] = {
                "url": url, "title": parser.title or prior.get("title", ""),
                "archive_path": dest.relative_to(ROOT).as_posix(), "sha256": sha,
                "first_seen": prior.get("first_seen", checked), "last_checked": checked,
                "status": "active", "discovered_from": prior.get("discovered_from", "seed" if url == SEED else "sitemap/link"),
            }
            for href, label in parser.links:
                linked = canonical(href, url)
                if linked and linked not in queued and relevant(linked + " " + label):
                    queue.append(linked)
                    queued.add(linked)
        except Exception as exc:
            failures.append(f"{url}: {exc}")
            if url in old:
                items[url] = old[url]

    if failures:
        for url, prior in old.items():
            items.setdefault(url, prior)
    write_outputs(items, old, checked, failures)
    print(f"Vic tracker: {len(items)} pages; {len(failures)} failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
