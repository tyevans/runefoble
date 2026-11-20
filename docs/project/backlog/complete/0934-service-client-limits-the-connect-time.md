---
id: '0934'
title: "The Service Client Limits the Connect Time to an Owner"
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0934: The Service Client Limits the Connect Time to an Owner

## Status

Complete

## Summary

When a Kubernetes Service still routes to a deleted pod, the gateway waited its full 5 s route timeout on the TCP connect. The caravan @game-session-down scenarios then got the 503 and the banner just after the 5 s Playwright wait, so they failed about one run in two.

## Problem Statement

- Gateway log: failing run `ConnectTimeout` 5.0 s after the click; passing run `ConnectError` at once.
- `libs/runefoble_platform/src/runefoble_platform/service_client/`: one timeout for connect and read.

## Documentation & Architecture Review

- ADR-0015: failures are visible and quick.

## Product & User Story References

- The e2e scenarios named below.

## Detailed Specification & Implementation Plan

1. `ServiceClient` limits the connect phase to `CONNECT_TIMEOUT_S = 2.0`; the read timeout stays per route.
2. Document it in `docs/reference/service-client.md`.

## Frontdoor Blackbox Test Plan

- Client test and gateway frontdoor test against an address that never answers: the 503 comes within the connect limit.
- Playwright on Kind: `caravan_board.feature` @game-session-down scenarios.

## Definition of Done

- Tests pass. Docs and CHANGELOG entry. The orchestrator runs the scenarios on Kind.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/caravan-503.md
