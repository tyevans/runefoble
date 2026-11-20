---
id: '0965'
title: Hosting Runbook for the Private Release One Cluster
status: Refined
created: 2026-11-19
dependencies:
- '0956'
- '0957'
- '0958'
- '0959'
- '0960'
- '0961'
- '0962'
- '0963'
- '0964'
governing_adrs:
- ADR-0005
- ADR-0019
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0965: Hosting Runbook for the Private Release One Cluster

## Status

Refined. Release One hosting slice 14, the last one (PRD-0025, outcome 8). It depends on slices 2 to 13. Writer C wrote the dependency list as the task list gives it (0956 to 0963), and added 0964, because the rehearsal uses the smoke job.

## Summary

Write one Diataxis how-to. It tells an operator how to install, upgrade, back up, restore, and rotate secrets on the private release cluster. Rehearse it once on a staging cluster. Each command in the page must run as written.

## Problem Statement

- No hosting how-to exists in `docs/how-to/`. The closest page, `docs/how-to/authenticate-with-zitadel-oidc.md`, covers the development setup.
- The chart has several hosted-only steps that an operator must run in order: the guard, the Secrets, the bootstrap hook, the PAT expiry, the backup, the restore test, and the Traefik pin.
- `Makefile:153-158` (`helm-deploy`) loads `values.local.yaml` when it exists. An operator must not use it. Document that.
- `zensical.toml:19` starts the How-To Guides list. The new page must be added to that list, or the docs build misses it.
- `values.yaml:204` has a comment that says "Set to false for the first install", but `values.yaml:205` sets `enabled: true`. Fix the comment in this record. This is a docs defect (AGENTS.md, Documentation directive: fix stale docs).

## Documentation & Architecture Review

- Diataxis (ADR-0019, `docs/project/adrs/accepted/adr-0019-agent-constitution-and-diataxis-documentation.md`): the page is a how-to (task steps for a reader who has a goal). Reference content stays in the reference pages from 0955, 0959, and 0961.
- `docs/how-to/` pattern: follow an existing how-to for the heading style.
- `docs/reference/hosted-profile.md` (0955) and `docs/reference/hosted-secrets.md` (0959): link them, do not copy them.

## Product & User Story References

- PRD-0025, Checkable Outcomes 4 to 6, and "What good looks like" 8.
- No user story. This is operator work.

## Detailed Specification & Implementation Plan

1. Create `docs/how-to/host-the-private-release-one-cluster.md`. It has these sections, in this order:
   1. Before you start: the decisions D1 to D12 and their owners (listed from the records).
   2. Install the platform: the Traefik version and the Traefik CRDs. The image digests (`values.images.yaml`). The storage class.
   3. Create the Secrets: the names and keys from `docs/reference/hosted-secrets.md`. Choose the source from D5.
   4. Check the render: `helm template` with the hosted example, `-f` only (never `values.local.yaml`). The guard message and the fix.
   5. Install: `helm upgrade --install --wait` with the explicit `-f` files. Explain why the bucket hook needs record 0933.
   6. First admin and invitations: the admin signs in, creates member accounts (D12), and confirms that registration is closed.
   7. Upgrade: each upgrade reruns the bootstrap Job (a Helm post-upgrade hook). The PAT expiry (D12b) and its rotation steps.
   8. Back up and restore: the backup CronJob, the bucket lifecycle rule (D8), the manual trigger, and the restore Job (off by default). State the empty-database rule.
   9. Rotate secrets: one entry per key in the reference table. For each key, the consumers that restart.
   10. Switch off the development paths: a checklist. Mailpit off, Swagger UI off, `/analytics` (D6), `devMode` false.
   11. Troubleshoot: the three most likely failures (guard, bucket Job, readiness `503` from the GPU endpoint).
2. Add the page to `zensical.toml` under "How-To Guides".
3. Fix `deployments/helm/runefoble/values.yaml:204` so the comment matches `enabled: true`. Name the value that is set and why. This edit is in the same change as 0965. (The edit does not change the file length.)
4. Rehearse on a staging cluster (a second Kind cluster is not enough for this; it needs a cluster with a real Traefik install and a real SMTP provider). Follow the page as written. Note every step that fails, and fix the page or the chart. Do not add steps that are not in the page.

Rules for this record:
- Every command in the page must exist in the Makefile, the chart, or a standard tool.
- The page never contains a secret value or an example password.
- Do not copy the reference tables. Link them.

### Inputs (user decisions)

- All decisions D1 to D12 from the hosting records. The page cannot be finished until each has an answer.

## Frontdoor Blackbox Test Plan

New file `tests/test_blackbox_docs_hosting_runbook.py`. It reads the page and the chart.
- The page exists under `docs/how-to/` and is listed in `zensical.toml`.
- Every fenced `helm` command in the page renders with the hosted example. Replace the `REPLACE-ME` placeholders in a temp copy first.
- Every `make` target named in the page exists in the `Makefile` (`make -n <target>` exits 0).
- Every relative link in the page resolves.
- The page does not contain the strings `runefoble_dev_password`, `admin:admin`, or `2099-01-01`.
- `make docs-build` passes.

Live rehearsal (staging, recorded in the PR): an operator who did not write the page installs the hosted release, creates a campaign, runs a backup, and restores it in a fresh namespace. The operator does this using only the page.

## Definition of Done

- The page passes the tests above and `make docs-build` passes.
- The staging rehearsal is recorded, with the steps that failed and their fixes.
- The `values.yaml:204` comment matches the value.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.
- `docs/reference/platform-services.md` links the page.

## Audit Provenance

- Severity: medium (no operator guide exists; errors are likely without one).
- Source audits: `.audit/research/r1-hosting.md`, sections 4, 12 (task 16). Lines were checked against `main` at `33885a70`. The comment drift at `values.yaml:204` is confirmed.
