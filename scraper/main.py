#!/usr/bin/env python3
"""Archive the public NDIS website into archive/ndis.

The scraper uses the NDIS HTML sitemap as its page inventory, respects robots.txt,
stores page/document bytes at stable paths, and maintains a hash manifest so Git
history becomes the version history of the archived site.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).with_name("config.json")
MANIFEST_NAME = "manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_if_changed(path: Path, value: Any) -> bool:
    rendered = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return True


def normalize_url(url: str, base_url: str) -> str | None:
    """Return a canonical same-site URL with fragments and query strings removed."""
    absolute = urljoin(base_url, url)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"}:
        return None

    base_host = urlsplit(base_url).hostname or ""
    host = parts.hostname or ""
    allowed_hosts = {base_host, base_host.removeprefix("www."), f"www.{base_host.removeprefix('www.')}"}
    if host not in allowed_hosts:
        return None

    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    canonical_host = urlsplit(base_url).netloc
    return urlunsplit(("https", canonical_host, path, "", ""))


def safe_parts(url: str) -> list[str]:
    path = unquote(urlsplit(url).path).strip("/")
    if not path:
        return ["home"]
    parts: list[str] = []
    for raw in path.split("/"):
        cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in raw).strip(".")
        parts.append(cleaned or "_")
    return parts


def page_path(archive_root: Path, url: str) -> Path:
    return archive_root / "pages" / Path(*safe_parts(url)) / "index.html"


def document_path(archive_root: Path, url: str) -> Path:
    return archive_root / "files" / Path(*safe_parts(url))


def build_robots(session: requests.Session, base_url: str, user_agent: str, timeout: int) -> RobotFileParser:
    robots_url = urljoin(base_url, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = session.get(robots_url, timeout=timeout)
        response.raise_for_status()
        parser.parse(response.text.splitlines())
    except requests.RequestException as exc:
        # Fail conservatively: if robots.txt cannot be read, stop instead of assuming permission.
        raise RuntimeError(f"Unable to read {robots_url}: {exc}") from exc
    return parser


def fetch(session: requests.Session, url: str, timeout: int, delay: float) -> requests.Response:
    time.sleep(delay)
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response


def discover_sitemap_links(html: bytes, sitemap_url: str, base_url: str, document_extensions: set[str]) -> tuple[set[str], set[str]]:
    soup = BeautifulSoup(html, "html.parser")
    pages: set[str] = set()
    documents: set[str] = set()

    for tag in soup.find_all("a", href=True):
        normalized = normalize_url(tag["href"], base_url)
        if not normalized:
            continue
        suffix = Path(urlsplit(normalized).path).suffix.lower()
        if suffix in document_extensions:
            documents.add(normalized)
        else:
            pages.add(normalized)

    pages.add(normalize_url(sitemap_url, base_url) or sitemap_url)
    return pages, documents


def discover_documents_from_page(html: bytes, page_url: str, base_url: str, document_extensions: set[str]) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    documents: set[str] = set()
    for tag in soup.find_all("a", href=True):
        normalized = normalize_url(tag["href"], base_url)
        if not normalized:
            continue
        suffix = Path(urlsplit(normalized).path).suffix.lower()
        if suffix in document_extensions:
            documents.add(normalized)
    return documents


def save_content_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def update_entry(
    manifest: dict[str, Any],
    url: str,
    relative_path: str,
    digest: str,
    content_type: str,
    now: str,
) -> str:
    entries = manifest.setdefault("entries", {})
    old = entries.get(url)

    if old is None:
        state = "new"
        first_seen = now
    elif old.get("sha256") != digest or old.get("status") != "active":
        state = "changed"
        first_seen = old.get("first_seen", now)
    else:
        state = "unchanged"
        first_seen = old.get("first_seen", now)

    if state != "unchanged":
        entries[url] = {
            "content_type": content_type,
            "first_seen": first_seen,
            "last_changed": now,
            "path": relative_path,
            "sha256": digest,
            "status": "active",
        }
    return state


def main() -> int:
    config = load_json(CONFIG_PATH, None)
    if not isinstance(config, dict):
        raise RuntimeError(f"Invalid config: {CONFIG_PATH}")

    base_url = config["base_url"]
    sitemap_url = config["sitemap_url"]
    user_agent = config["user_agent"]
    timeout = int(config.get("request_timeout_seconds", 30))
    delay = float(config.get("request_delay_seconds", 0.35))
    max_pages = int(config.get("max_pages", 5000))
    document_extensions = {ext.lower() for ext in config.get("document_extensions", [])}

    archive_root = REPO_ROOT / config["archive_root"]
    archive_root.mkdir(parents=True, exist_ok=True)
    manifest_path = archive_root / MANIFEST_NAME
    manifest = load_json(manifest_path, {"format_version": 1, "entries": {}})
    if not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), dict):
        raise RuntimeError(f"Invalid manifest: {manifest_path}")

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8"})

    robots = build_robots(session, base_url, user_agent, timeout)
    if not robots.can_fetch(user_agent, sitemap_url):
        raise RuntimeError(f"robots.txt does not permit fetching {sitemap_url} for {user_agent}")

    now = utc_now()
    errors: list[dict[str, str]] = []
    changes: dict[str, list[str]] = {"new": [], "changed": [], "missing": [], "restored": []}
    seen_urls: set[str] = set()

    print(f"Fetching sitemap: {sitemap_url}")
    sitemap_response = fetch(session, sitemap_url, timeout, delay)
    page_urls, document_urls = discover_sitemap_links(
        sitemap_response.content, sitemap_url, base_url, document_extensions
    )

    if len(page_urls) > max_pages:
        raise RuntimeError(f"Sitemap exposed {len(page_urls)} pages; configured maximum is {max_pages}")

    print(f"Discovered {len(page_urls)} pages from the NDIS sitemap")

    # Pages are fetched first because they can expose downloadable documents not listed in the sitemap.
    for index, url in enumerate(sorted(page_urls), start=1):
        if not robots.can_fetch(user_agent, url):
            print(f"SKIP robots.txt: {url}")
            continue
        try:
            response = sitemap_response if url == normalize_url(sitemap_url, base_url) else fetch(session, url, timeout, delay)
            data = response.content
            path = page_path(archive_root, url)
            rel = path.relative_to(REPO_ROOT).as_posix()
            digest = sha256_bytes(data)
            old_status = manifest["entries"].get(url, {}).get("status")
            state = update_entry(manifest, url, rel, digest, response.headers.get("Content-Type", ""), now)
            if state in {"new", "changed"}:
                save_content_if_changed(path, data)
                changes[state].append(url)
                if old_status == "missing":
                    changes["restored"].append(url)
            seen_urls.add(url)
            if "html" in response.headers.get("Content-Type", "").lower() or not response.headers.get("Content-Type"):
                document_urls.update(discover_documents_from_page(data, url, base_url, document_extensions))
            print(f"[{index}/{len(page_urls)}] {state.upper():9} {url}")
        except requests.RequestException as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"ERROR {url}: {exc}", file=sys.stderr)

    print(f"Discovered {len(document_urls)} linked documents")
    for index, url in enumerate(sorted(document_urls), start=1):
        if not robots.can_fetch(user_agent, url):
            print(f"SKIP robots.txt: {url}")
            continue
        try:
            response = fetch(session, url, timeout, delay)
            data = response.content
            path = document_path(archive_root, url)
            rel = path.relative_to(REPO_ROOT).as_posix()
            digest = sha256_bytes(data)
            old_status = manifest["entries"].get(url, {}).get("status")
            state = update_entry(manifest, url, rel, digest, response.headers.get("Content-Type", ""), now)
            if state in {"new", "changed"}:
                save_content_if_changed(path, data)
                changes[state].append(url)
                if old_status == "missing":
                    changes["restored"].append(url)
            seen_urls.add(url)
            print(f"[file {index}/{len(document_urls)}] {state.upper():9} {url}")
        except requests.RequestException as exc:
            errors.append({"url": url, "error": str(exc)})
            print(f"ERROR {url}: {exc}", file=sys.stderr)

    # Never delete historical archive files. If something disappears from the sitemap/current pages,
    # mark it missing once and let Git history preserve the last captured version.
    for url, entry in list(manifest["entries"].items()):
        if url not in seen_urls and entry.get("status") == "active":
            entry["status"] = "missing"
            entry["missing_since"] = now
            changes["missing"].append(url)

    material_change = any(changes[key] for key in changes)
    if material_change:
        report = {
            "checked_at": now,
            "counts": {key: len(value) for key, value in changes.items()},
            "changes": changes,
            "errors": errors,
        }
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        write_json_if_changed(archive_root / "changes" / f"{stamp}.json", report)
        write_json_if_changed(manifest_path, manifest)
    elif not manifest_path.exists():
        write_json_if_changed(manifest_path, manifest)

    print(
        "Done. "
        + ", ".join(f"{name}={len(values)}" for name, values in changes.items())
        + f", errors={len(errors)}"
    )
    if errors:
        print("Some URLs failed; successful captures were retained. See workflow logs for details.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
