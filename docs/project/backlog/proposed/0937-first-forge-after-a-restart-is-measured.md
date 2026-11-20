---
id: '0937'
title: The First Forge After an asset_forge Restart Is Measured
status: Proposed
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0937: The First Forge After an asset_forge Restart Is Measured

## Status

Proposed.

## Summary

In one full e2e run on Kind, right after a rollout restart, the battlemap preview did not show within 5 s although the forge answered 200. Alone, the forge scenarios pass in about 2 s, and a later full run passed. The first forge after a start may do slow one-time work.

## Problem Statement

- `.audit/work/e2e_full9.log` and the eighth run notes: one failure of "Forging a battlemap sends the prompt and shows the forged preview" right after a restart.

## Detailed Specification & Implementation Plan

1. Add a duration span or log to the forge route and the asset read (OpenTelemetry how-to).
2. Measure the first and later forges after a restart on Kind. If the first is slow, do the one-time work at start-up (before `/readyz` is ready), not on the first request. Do not raise the test timeout.

## Frontdoor Blackbox Test Plan

- Measurement only, then a regression test for any start-up change.

## Definition of Done

Measured; fixed or closed with the numbers.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/e2e_full9.log
