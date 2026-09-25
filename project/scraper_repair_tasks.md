# Scraper repair tasks

Updated: 25 September 2026 (Australia/Melbourne).
Scope: myNDISwiki/MyNDIS. Status is based on inspected workflow logs, not just green run badges.

## Completed and verified

- [x] Fix unstaged generated files preventing five archive workflows from pushing results.
  Commit: [a6d1aaf](https://github.com/myNDISwiki/MyNDIS/commit/a6d1aaf8b85aa7b7f25d990c5f7fb53c22ad187c).
  Live pushes subsequently succeeded for NDIS, Health, government pages, data/research and Victoria.
- [x] Enable multi-run queuing for all nine archive-writer workflows.
  Commit: [b31a77f](https://github.com/myNDISwiki/MyNDIS/commit/b31a77fc44cfc42ece08cffd9a0523d74fb225ac).
  No archive queue cancellations observed in the 25 September check.
- [x] Implement Engage NDIS Mapbox secret-token redaction before writing captures and extracting links.
  Per-page metadata records occurrence counts and separate received/stored SHA-256 hashes.
  Offline tests cover repeated tokens, unchanged ordinary content, archive output, repeat runs and failed-fetch retention.
  This is targeted Mapbox redaction, not a general guarantee that every type of credential is detected.

## Priority 1 — Complete live verification and fix remaining workflow failures

- [ ] Confirm a fresh Engage NDIS run passes push protection and saves captures.
  Inspect the manifest redaction counts and successful push. Keep GitHub secret protection enabled.
  Do not test or publish the captured credential.
  Evidence: [blocked run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36068373469).
- [ ] Fix standalone change-history builder merge conflicts.
  Sync with current main before generating pages; check checkout history and ensure all generated outputs are staged.
  Verify queued runs do not regenerate from stale snapshots and fail during rebase.
  Evidence: [failed run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36016417506).
  Conflicted files: archive/reports/README.md, archive/reports/dashboard.json, project/dashboard.html.
- [ ] Make incomplete captures visible in workflow summaries and dashboard status.
  Preserve successful captures, but distinguish complete, partial and failed runs.
  Verify that continued-on-error scraper failures cannot be mistaken for complete coverage.

## Priority 2 — Resolve capture gaps

- [ ] Health NDIS: investigate 403 responses for public consultation documents using supported public download routes.
  Record inaccessible resources explicitly; do not bypass access restrictions.
  Evidence: [Health run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36061706221).
- [ ] Government pages: investigate timeouts on the national autism strategy page, reference-group page and its terms of reference.
  Evidence: [government run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36057162547).
- [ ] Data/research: reconcile the 25 failed resources from the latest inspected run.
  Distinguish stale or incorrectly resolved 404 links from unavailable external resources.
  Keep the external robots.txt 403 recorded as an access gap; do not bypass it.
  Evidence: [data/research run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36066734029).
- [ ] NDIS: repair or explicitly mark the missing 13–14 May 2025 PRG meeting-summary DOCX link.
  Confirm the actual link target from its public source page before changing the URL.
  Evidence: [NDIS run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36055074166).

## Observe — no current repair established

- [ ] Watch for recurring GitHub Pages deployment failures.
  One deployment returned GitHub HTTP 503; later deployments succeeded.
  Evidence: [503 run](https://github.com/myNDISwiki/MyNDIS/actions/runs/36027278260).
- Latest inspected Victoria, NDIS Review and NDIS Commission runs saved successfully with no errors found in their logs.

## Completion criteria

- Each tracker completes a fresh run and pushes its results.
- Every inaccessible resource appears in a gap report; a green workflow alone is not proof of full coverage.
- Archive writers queue without replacing waiting runs.
- Generated-page builds and website deployment succeed.
