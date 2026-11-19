---
id: '0907'
title: "The Campaign List Reads Campaigns and Permissions Without N+1 Sequential Calls"
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0907: The Campaign List Reads Campaigns and Permissions Without N+1 Sequential Calls

## Status

Complete

## Summary

`GET /api/v1/campaigns` handles each campaign in sequence: two aggregate loads, a role lookup and five permission checks. For a DM with about 17 campaigns it passes the 5 s gateway timeout, and the App Shell shows "Upstream service is unavailable".

## Problem Statement

- `services/game_session/src/game_session/campaign/service_campaigns.py:180-197`, `_summarize` (:104-111), `role_for` (:73-77).
- `permission_flags.py:24-32`: five sequential checks per campaign.
- Gateway log: `ReadTimeout` -> `GET /api/v1/campaigns 503`.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. Measure first: add a span or a duration log for `list_campaigns` (OpenTelemetry how-to).
2. Load the campaigns concurrently (bounded), and compute permissions with concurrent checks or SpiceDB bulk checks / `LookupResources` per permission.
3. Do not raise the gateway timeout.

## Frontdoor Blackbox Test Plan

- Blackbox: a caller with 25 campaigns gets the list with correct roles and flags, and the number of sequential SpiceDB round trips does not grow with the campaign count (assert through a counting SpiceDB double at the process boundary, or time against a live SpiceDB container).
- Playwright on Kind (orchestrator): `campaign_members_manage.feature`.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: high
- Source audits: .audit/reports/e2e-triage-1.md
