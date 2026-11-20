---
id: '0977'
title: The Whisper Bar Approve, Modify, and Send to Table Actions Reach The Watcher
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

# TASK-0977: The Whisper Bar Approve, Modify, and Send to Table Actions Reach The Watcher

## Status

Proposed

## Summary

`services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts` dispatches `action-approved`, `action-modified` and `narration-send`. No App Shell listener exists (`frontend/src/views/session-view.ts`). Only `action-vetoed` has a listener (TASK-0949). Add listeners that call the Watcher routes, and show call errors in the bar.

## Source

Found during TASK-0949. See the TASK-0949 report, section Discovered.
