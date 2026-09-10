# Contributing to MyNDIS

MyNDIS preserves primary NDIS source material and develops an evidence-based public guide. Contributions should make the source, provenance, and change history easier to inspect.

Before starting work, contributors should also check the companion [`ai-skills`](https://github.com/ksouth/ai-skills) repository for reusable principles, workflows, templates, and project handoffs. Load only the guidance relevant to the task, and follow its recovery, verification, provenance, and non-destructive editing rules.

## Before changing anything

Read the repository [README](README.md), inspect the relevant folder and workflow, and check the current Git status. Recover existing scripts, archives, reports, and project notes before creating a replacement.

Keep these categories separate:

| Folder | Use |
|---|---|
| `archive/` | Preserved source material and machine-generated archive outputs |
| `scraper/` | NDIS website archive code and configuration |
| `project/` | Tracker code, source lists, dashboard code, and project planning |
| `wiki/` | Public-facing Docusaurus content and site configuration |
| `draft/` | Deliberately unfinished or review-stage material |
| `working/` | Temporary working files and intermediate material |

Do not mix interpretation into a raw source archive. Put explanations in the wiki or project documentation and link them back to the relevant source.

## Source and archive rules

- Prefer the original government page, document, dataset, or source code when checking a fact.
- Preserve the source URL, capture date, downloaded bytes, and hash whenever the relevant tracker supports them.
- Do not silently replace or delete historical archive material.
- A missing, timed-out, forbidden, or changed URL must be recorded as such. A failed request is not evidence that a source was deleted.
- Keep partial captures and their failure reports. Do not describe a partial run as complete.
- Treat external links, embedded dashboards, and interactive services as separate sources unless an explicit adapter has been added.
- Remove credentials, private information, and accidental secrets before committing. Do not archive material that is not publicly available or within the task's scope.

## Adding or changing a tracker

Use the existing tracker that most closely matches the source:

- `scraper/main.py` archives the main `www.ndis.gov.au` site.
- `scraper/dataresearch.py` archives the separate data and research site.
- `project/gov_tracker.py` handles configured government pages in `project/gov-sources.json`.
- `project/health_ndis_tracker.py` and `project/vic_gov_tracker.py` handle their specialist source sets.

Before adding a new tracker, check whether the existing configuration can represent the source. If a new tracker is needed, document its scope, crawl starting points, robots handling, URL limits, failure behaviour, output paths, and schedule.

Every tracker should leave enough evidence to answer:

1. What URLs or files were discovered?
2. What was captured successfully?
3. What changed since the previous capture?
4. What failed, was excluded, or remains pending?
5. Which bytes and hashes are authoritative for the captured copy?

Use a bounded run when testing. Review the resulting archive and run report before committing. For large files, preserve a verified reconstruction method and record the full-file hash.

## Wiki and documentation

Public wiki content belongs in `wiki/docs/` and should link claims to official sources. Keep the site-wide independence disclaimer visible through the global site layout. Update `project/wiki-information-architecture.md` when a structural change affects navigation or content ownership.

Documentation should state whether a passage is source-derived, reported by a participant, inferred, unresolved, or current project guidance. Do not turn an association into a diagnosis, legal conclusion, or causal claim without supporting evidence.

## Validation

Run the narrowest meaningful checks for the change and record the result in the pull request or commit notes. Typical checks include:

```bash
python -m py_compile scraper/*.py project/*.py
python -m unittest discover -s scraper
python project/build_dashboard.py
```

For wiki changes, run the build from `wiki/` when dependencies are available. For archive changes, inspect the manifest, change log, per-page history, and latest run report. Confirm that failed requests did not overwrite a good prior capture.

## Commits and pull requests

Use small, descriptive commits that explain the completed change, for example:

```text
Add data research archive gap reporting
Update FOI source coverage documentation
Fix dashboard count for government tracker
```

A pull request should state the problem, the resulting behaviour, the files or source set affected, validation performed, and any known gaps. Include the exact source URL or archive path for source additions. Link relevant run reports or change logs when they contain the evidence for the change.

Do not commit generated archive output from an ad hoc local run unless that output is intentionally part of the change. Scheduled workflows may commit their own verified archive updates.

## Safety and provenance

Preserve authorship and existing work. Do not use destructive cleanup, broad deduplication, or automatic master-data edits. If a substantive existing instruction or authored document needs revision, create a clearly versioned successor and leave the original available for review.

MyNDIS is independent of the NDIA and the Australian Government. Public-facing pages must retain that distinction.
