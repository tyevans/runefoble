---
id: '0976'
title: The Gateway Passes an Engine-Unavailable 503 Body to the Browser
status: Proposed
created: 2026-11-20
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0002
governing_prds:
- PRD-0025
governing_stories: []
target_bc: gateway
target_release: 1.0.0
---

# TASK-0976: The Gateway Passes an Engine-Unavailable 503 Body to the Browser

## Status

Proposed

## Summary

`gateway/api/src/gateway_api/upstream_errors.py:47-53` maps every owner `5xx` to `502` with a generic body. Thus an engine-unavailable `503` body (`error`, `backend`, `message`) from an engine port route never reaches the browser. ADR-0015 requires that the user sees why an engine is not available. TASK-0949 added `narration_engine` to the whisper list as a workaround. Pass the owner `503` body through for engine port routes, with a blackbox gateway test for each route.

## Source

Found during TASK-0949. See the TASK-0949 report, section Discovered.
