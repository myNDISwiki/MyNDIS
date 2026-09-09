# NDIS Archive Scraper

This directory contains the automated scraper used to archive the public NDIS website into `archive/ndis/`.

The scraper is run by `.github/workflows/archive-ndis.yml`. It can be started manually from the repository's **Actions** tab using **Archive NDIS website → Run workflow**, and it also runs automatically on its configured schedule.

`main.py` reads `config.json`, checks the NDIS sitemap and `robots.txt`, downloads current pages and linked documents, compares SHA-256 hashes against the archive manifest, and writes only material changes. Historical files are retained rather than deleted when a page disappears.

Changes to files in this `scraper/` directory also trigger the workflow automatically. This README was added as the initial live-run trigger after setup.

## Data and research full-site archive

`python scraper/dataresearch.py` separately archives `https://dataresearch.ndis.gov.au/`.
It starts at the homepage and sitemap, recursively follows public same-host links,
retains meaningful query parameters (including pagination), and downloads linked
publications on other hosts. HTML, CSS, scripts and images referenced by the site
are captured too. Each redirect destination is checked against its own robots rules.

Outputs are in `archive/dataresearch/`: a URL/hash manifest, raw resource files,
per-resource wording histories, a cumulative CSV change log, and dated run reports.
Existing versions are preserved by Git history after each committed run. Resources
are rechecked even if their links disappear. Failed requests never replace a good
capture. HTTP errors are reported as capture gaps, not assumed to prove deletion.

Files larger than 25 MiB are stored as numbered `content.part-00000` chunks. Join the
files in the exact `files` order in `metadata.json` to recover the original bytes;
the recorded SHA-256 covers the complete original, not individual chunks. The source
URL preserves the original filename. Smaller documents use `content.bin`.

The daily GitHub workflow runs at 05:11 Australia/Melbourne. It retains successful
captures and gap reports before marking an incomplete run failed. Bounded runs save
a pending URL queue, which the next run processes first; it does not silently drop
resources beyond the time or URL limit. Run `python -m unittest discover -s scraper
-p 'test_dataresearch.py'` to test the archive safeguards.

Coverage means discoverable public source bytes, not an offline recreation of every
interactive service. External embeds (including dashboards/video players) and
external non-document links are listed with their referring pages in
`latest-run.json`; live dashboard APIs, interactive filters, and third-party video
streams require separate adapters. Robots exclusions and failed downloads are
explicit. Content with no public link cannot be discovered by this crawl.

Restore a file (small or chunked) with integrity checking:

```bash
python scraper/restore_dataresearch.py archive/dataresearch/resources/URL_HASH/metadata.json /tmp/original-filename.xlsx
```

The output must not already exist. The restore command verifies both the byte count
and full-file SHA-256 and removes an incomplete output if verification fails.
