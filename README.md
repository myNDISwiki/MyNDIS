# MyNDIS

MyNDIS is an independent project for preserving primary NDIS source material and building a practical, evidence-based guide to navigating the National Disability Insurance Scheme.

This repository separates source archives, working material, project documentation, scraper code, drafts, and the eventual public-facing wiki so that historical evidence is not mixed with interpretation.

## Repository structure

```text
MyNDIS/
├── wiki/                 Public-facing guide and wiki material
├── archive/              Preserved source material
│   ├── press/            Journalism and media coverage
│   ├── gov/              Government and parliamentary material
│   ├── ndis/             Automated archive of the NDIS website
│   └── research/         Research papers and other evidence
├── scraper/              NDIS website archiving software
├── project/              Project planning and documentation
├── draft/                Draft material
├── working/              Temporary working material
└── .github/workflows/    GitHub automation
```

Empty directories contain `.gitkeep` files because Git does not otherwise preserve empty folders.

## Public wiki

The public-facing MyNDIS wiki will use **Docusaurus**, with its content stored as Markdown/MDX in this repository. The site should be designed mobile-first, with clear practical navigation rather than reproducing the organisational structure of the NDIA website.

The primary user routes are:

- **I want to apply for the NDIS**
- **I am on the NDIS**

The canonical detailed wiki structure and content plan is maintained in **[project/wiki-information-architecture.md](project/wiki-information-architecture.md)**. Earlier proposals, drafts, and process documents are retained as part of the project history rather than deleted when the plan evolves.

The wiki should preserve stable URLs, support multilingual content, expose useful metadata and sitemaps, and link claims and practical guidance back to relevant primary sources wherever possible.

### Site-wide disclaimer

Every public MyNDIS page must display the following disclaimer at the bottom of the page. It should be implemented globally in the site layout/footer rather than copied manually into individual Markdown files:

> **MyNDIS is an independent information project and is not an official Australian Government or NDIA website. Information is maintained and updated as carefully as possible, but may become outdated or contain errors. Always check relevant official sources when making decisions about your NDIS supports, rights, or obligations.**

The disclaimer must remain clearly visible and should not be hidden behind a menu, modal, or separate legal page.

### Keywords and concept index

MyNDIS should include a controlled **keyword/concept index** that maps important NDIS concepts across both the MyNDIS wiki and official source material. This is distinct from ordinary tags used to classify MyNDIS articles.

A concept page such as `/keywords/evidence/` should be able to contain:

- a plain-language explanation of the concept in an NDIS context;
- links to relevant MyNDIS guides;
- links to current official NDIS pages where the concept or controlled search terms appear;
- links to the corresponding archived NDIS pages;
- links to relevant legislation, rules, operational guidance, or other primary sources where appropriate; and
- related concepts and terminology, including alternative official language used for substantially the same idea.

The keyword vocabulary should be centrally controlled so that variants such as `evidence`, `Evidence`, and overlapping synonyms do not accidentally become unrelated indexes.

Where practical, the NDIS archive should support automated keyword discovery. A script can search the visible text of archived NDIS pages for each controlled term and regenerate the source-occurrence portion of the concept index. Human-authored explanations and relationships should remain separate from automatically generated occurrence lists.

The purpose is not merely to count words. It is to let a user start with a concept such as **evidence** and discover where that concept appears across otherwise disconnected parts of the NDIS information system.

## NDIS website archive

The automated archive lives under `archive/ndis/`.

The scraper starts from the official NDIS sitemap at:

`https://www.ndis.gov.au/sitemap`

It uses that page as the inventory of public NDIS web pages, then checks each same-domain page and collects downloadable documents linked from those pages, including PDFs, Word files, spreadsheets, text files, and ZIP files.

The scraper does **not** delete an archived page when it disappears from the live NDIS website. A missing page is marked as missing in the manifest while its last captured copy remains in the repository. This matters because deletion or replacement of official information can itself be historically important.

### Archive layout

After the first scraper run, `archive/ndis/` will contain:

```text
archive/ndis/
├── pages/                Raw HTML snapshots of NDIS pages
├── files/                Downloaded documents linked from NDIS pages
├── changes/              JSON reports for runs that found material changes
└── manifest.json         Current URL, file path, status, and SHA-256 hash index
```

Page paths mirror the source URL. For example:

`https://www.ndis.gov.au/participants`

is stored as:

`archive/ndis/pages/participants/index.html`

Git provides the version history. When the NDIS changes a page, the scraper replaces the current snapshot at the same path and Git preserves the previous version in commit history.

## How change detection works

For every captured page or document, the scraper calculates a SHA-256 hash of the downloaded bytes and compares it with the hash recorded in `archive/ndis/manifest.json`.

- A URL not previously recorded is marked **new**.
- A known URL with different bytes is marked **changed**.
- A page that disappears from the NDIS sitemap is marked **missing**, but its archived file is retained.
- A previously missing page that returns is captured again and recorded as restored.
- An unchanged URL produces no repository change.

A timestamped JSON report is written to `archive/ndis/changes/` only when a material change is detected. Routine checks that find nothing new do not create pointless commits.

Download failures are printed in the GitHub Actions run log. A transient request failure does not cause an archived page to be treated as deleted.

## Automatic checks

The workflow is defined in:

`.github/workflows/archive-ndis.yml`

GitHub Actions runs the scraper **every day at 3:17 am Australia/Melbourne time**. It deliberately runs at 17 minutes past the hour rather than exactly on the hour, because GitHub notes that scheduled Actions can be delayed during periods of high load near the start of an hour.

The workflow can also be run manually from the repository's **Actions** tab using **Archive NDIS website → Run workflow**.

Each run:

1. Checks out the latest `main` branch.
2. Installs Python and the scraper dependencies.
3. Runs `python scraper/main.py`.
4. Compares the resulting archive with the repository.
5. If nothing changed, finishes without creating a commit.
6. If something changed, commits the updated archive to `main` with the author `MyNDIS Archive Bot` and pushes it to GitHub.

The workflow has only the repository permission it needs for this job: `contents: write`.

GitHub can automatically disable scheduled workflows in public repositories after 60 days with no repository activity. If that ever happens, the workflow can be re-enabled from the Actions tab.

## Scraper behaviour and limits

Configuration is in `scraper/config.json`.

Current safeguards include:

- The scraper only archives `ndis.gov.au` / `www.ndis.gov.au` URLs.
- URL fragments and query strings are removed before archiving so tracking parameters do not create duplicate files.
- `robots.txt` is checked before scraping. If the scraper cannot read `robots.txt`, it stops rather than assuming permission.
- Requests use an identifiable project user-agent: `MyNDISArchiveBot/1.0 (+https://github.com/myNDISwiki/MyNDIS)`.
- A delay is inserted between requests to avoid hammering the NDIS server.
- The page count is capped at 5,000 as a safety check. If the sitemap unexpectedly exceeds that limit, the run stops instead of blindly crawling an abnormal number of URLs.
- Historical archive files are retained rather than automatically deleted.

The scraper intentionally does not attempt to mirror external websites linked by the NDIS. Those sources can be archived separately in the appropriate repository folders if required.

## Running the scraper locally

Python 3.12 is used by the automated workflow.

```bash
python -m pip install -r scraper/requirements.txt
python scraper/main.py
```

The scraper writes directly into `archive/ndis/`. Review the resulting Git diff before committing when running it manually.

## Scraper files

```text
scraper/
├── main.py               Scraper and change-detection logic
├── config.json           Site, timing, and file-type configuration
└── requirements.txt      Python dependencies
```

The implementation currently uses `requests` for HTTP requests and `BeautifulSoup` for HTML link extraction.

## Source integrity

The NDIS website archive is intended to preserve source material, not silently rewrite it. HTML pages and downloadable files are stored as downloaded. The manifest records SHA-256 hashes so a captured file can be checked against the version recorded by the scraper.

The current copy of a page is therefore easy to inspect in the repository, while previous copies remain recoverable through Git history.

## Independence

MyNDIS is an independent archival and documentation project. It is not operated by, endorsed by, or affiliated with the National Disability Insurance Agency or the Australian Government.
