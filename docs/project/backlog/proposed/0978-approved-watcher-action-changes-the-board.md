---
id: '0978'
title: An Approved or Expired Watcher Action Changes the Board
status: Proposed
created: 2026-11-20
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0002
governing_prds:
- PRD-0025
governing_stories: []
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0978: An Approved or Expired Watcher Action Changes the Board

## Status

Proposed

## Summary

`services/the_watcher/src/the_watcher/routers/copilot/actions.py:20-26`: `propose` passes no execute callback. An approved action, or an action whose pause window expires, changes no board state. Thus the veto window guards nothing on the board. Give the proposal an executor that applies the action through the owning service, and test approve, expire and veto through the public routes.

## Source

Found during TASK-0949. See the TASK-0949 report, section Discovered.
