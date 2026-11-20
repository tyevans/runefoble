---
id: '0971'
title: A Spoken Move to a Named Token Reads the Board Once and Fits the Gateway Budget
status: Proposed
created: 2026-11-19
dependencies:
- '0948'
governing_adrs:
- ADR-0022
- ADR-0015
governing_prds:
- PRD-0025
governing_stories:
- us-0001-player-commands-board-via-voice
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0971: A Spoken Move to a Named Token Reads the Board Once and Fits the Gateway Budget

## Status

Proposed

## Summary

A spoken move to a named token reads the board twice: once in `WorkerIntentParser.parse` (`fetch_visible_tokens`) and again in `routers/intent/speech.py` `_destination`. The worst case is intent 2 s + board 2 s + board 2 s + proposal 2 s = 8 s, equal to the gateway speech budget of 8 s (`.audit/work/0948.md`, Discovered 4). Read the visible tokens once per request and pass them to the destination resolver, so the worst case has a margin under the gateway budget. A blackbox test with slow live loopback upstreams checks that the Watcher answers before the gateway budget ends.
