---
id: '0884'
title: Atlas Permissions Use the atlas Object or the Definition Goes
status: Proposed
created: 2026-11-19
dependencies:
- TASK-0768
governing_adrs:
- ADR-0001
governing_prds:
- PRD-0023
governing_stories:
- US-0050
target_release: 0.9.0
---

# TASK-0884: Atlas Permissions Use the atlas Object or the Definition Goes

## Status
Proposed

Source: TASK-0768 report (`.audit/work/0768.md`).

## Summary
`libs/runefoble_auth/schema/runefoble.zed` defines `atlas` with `place_pin` and `edit`, but no code writes an `atlas#campaign` tuple. campaign_lore checks `campaign.play` for pin placement, which allows the same subjects today. Decide: write the atlas tuple when a campaign atlas is created and check `atlas.place_pin` and `atlas.edit`, or remove the `atlas` definition and keep the campaign checks. An unused definition is drift.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
