# NDIS Archive Scraper

This directory contains the automated scraper used to archive the public NDIS website into `archive/ndis/`.

The scraper is run by `.github/workflows/archive-ndis.yml`. It can be started manually from the repository's **Actions** tab using **Archive NDIS website → Run workflow**, and it also runs automatically on its configured schedule.

`main.py` reads `config.json`, checks the NDIS sitemap and `robots.txt`, downloads current pages and linked documents, compares SHA-256 hashes against the archive manifest, and writes only material changes. Historical files are retained rather than deleted when a page disappears.

Changes to files in this `scraper/` directory also trigger the workflow automatically. This README was added as the initial live-run trigger after setup.
