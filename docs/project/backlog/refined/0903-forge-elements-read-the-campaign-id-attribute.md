---
id: '0903'
title: "Forge Elements Read the campaign-id Attribute and Refuse to Submit Without It"
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0903: Forge Elements Read the campaign-id Attribute and Refuse to Submit Without It

## Status

Refined.

## Summary

The App Shell sets the `campaign-id` attribute on the Asset Forge and Print Forge elements, but the elements declare `campaignId` with no `attribute:` option, so Lit watches `campaignid`. Every forge request goes out with no campaign id, and since TASK-0902 the server answers 422.

## Problem Statement

- `services/asset_forge/ui/src/runefoble-asset-forge.ts:22-23`, `runefoble-print-forge.ts:26-27`: `@property({ type: String }) campaignId = ''`.
- `frontend/src/views/campaign-hub-view.ts:88-89` sets `campaign-id=${app.campaignId}`.
- The UI sends `campaign_id: undefined` (`runefoble-print-forge.ts:109,119`; `runefoble-asset-forge.ts:101`).
- Failing scenarios: asset_forge preview and PDF export, asset_forge_composition preview.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. Add `attribute: 'campaign-id'` to both elements.
2. With no campaign id, the element shows a clear message and sends no request (ADR-0015). It never sends `undefined`.
3. Unit or DOM test: setting the attribute sets the property, and the request body carries the id.
4. Storybook stories pass a campaign id.

## Frontdoor Blackbox Test Plan

- DOM test of both elements: attribute to property, and no request without a campaign id.
- Playwright on Kind (orchestrator): `asset_forge.feature` and `asset_forge_composition.feature`.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: high
- Source audits: .audit/reports/e2e-triage-1.md
