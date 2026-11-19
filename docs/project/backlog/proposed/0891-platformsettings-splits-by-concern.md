---
id: '0891'
title: PlatformSettings Splits Into Settings per Concern
status: Proposed
created: 2026-11-19
dependencies:
- '0720'
governing_adrs:
- ADR-0003
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0891: PlatformSettings Splits Into Settings per Concern

## Status

Proposed. Step 5 of TASK-0720 (`.audit/work/0720.md`).

## Summary

TASK-0720 moved the SpiceDB settings into `runefoble_auth.settings.SpiceDBSettings`. `PlatformSettings` in `libs/runefoble_platform/src/runefoble_platform/config.py` still holds storage (Silo), telemetry (OTel), mail (SMTP and Mailpit), the gateway upstream URLs, and four bounded-context settings classes. Each service reads settings it does not use. Split them so each service reads only its own settings and fails at start-up only for settings it needs.

## Problem Statement

- `libs/runefoble_platform/src/runefoble_platform/config.py`: one class for all concerns.
- Root `conftest.py` sets env names for every owner URL field, because every service builds the full class.

## Detailed Specification & Implementation Plan

Refine into one slice per concern (storage, telemetry, mail, gateway upstreams), each under 15 files. Update every call site. No aliases.

## Frontdoor Blackbox Test Plan

Per slice: a service that does not use the concern starts without its env; a service that uses it fails at start-up with `ConfigurationError` when a required value is missing.

## Definition of Done

Refined slices filed.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0720.md
