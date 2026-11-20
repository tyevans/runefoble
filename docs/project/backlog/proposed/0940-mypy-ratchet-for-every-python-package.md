---
id: '0940'
title: The Lint Gate Type-Checks Every Python Package With a Ratchet
status: Proposed
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0010
governing_prds: []
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0940: The Lint Gate Type-Checks Every Python Package With a Ratchet

## Status

Proposed

## Summary

`make lint` runs mypy on two packages only (`services/inference_worker/src`, `gateway/mcp/src/gateway_mcp`; `Makefile:272-275`). On 2026-11-19 the TASK-0936 merge removed a `ServiceClient` parameter that `voice_agent` still passed. Lint passed, and 13 tests failed later in the full gate. A type check of `voice_agent` would have found it at once.

## Problem Statement

mypy error counts on 2026-11-19: `libs/runefoble_platform/src` 6, `gateway/api/src` 157, `services/voice_agent/src` 152, `services/board_state/src` 219, `services/game_session/src` 627. One large clean-up is not small. A ratchet stops the count from growing and lets it fall package by package.

## Scope

1. A script runs mypy on every workspace package and compares the error count of each package with a committed baseline file. More errors than the baseline fails the gate. Fewer errors lowers the baseline in the same change.
2. `make lint` runs the script. The two packages at zero stay at zero.
3. `libs/runefoble_platform` goes to zero in this task (6 errors), because every service imports it.

## Test Plan

- Add one type error to a package: the gate fails and names the package. Fix it: the gate passes.
