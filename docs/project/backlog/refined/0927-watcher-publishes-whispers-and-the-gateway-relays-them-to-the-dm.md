---
id: '0927'
title: The Watcher Publishes Whispers, and the Gateway Relays Them Only to the DM
status: Refined
created: 2026-11-19
dependencies:
- '0923'
governing_adrs:
- ADR-0001
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: the_watcher
target_release: 0.9.0
---

# TASK-0927: The Watcher Publishes Whispers, and the Gateway Relays Them Only to the DM

## Status

Refined. Follow-up of TASK-0923 (`.audit/work/0923.md`).

## Summary

The Watcher saves `WhisperRecorded` in its aggregate but publishes no event, so no live `dm_whisper` frame can reach the DM. Before TASK-0910 the frame came only from clients, and any player could forge it. Publish the whisper event and let the gateway session frame consumer (TASK-0923) relay it to DM sockets only.

## Problem Statement

- `WhisperRecorded` is saved without a publisher (see `.audit/work/0923.md`).
- `gateway/api/src/gateway_api/session_frames.py`: `dm_whisper` is a server kind with no producer after TASK-0923.

## Documentation & Architecture Review

- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: a whisper is private to the DM.
- `docs/reference/redis-streams-event-bus.md`: publish policy. A whisper is a DM decision path, so it uses `publish_or_fail`.

## Product & User Story References

- The DM copilot whisper channel.

## Detailed Specification & Implementation Plan

1. The Watcher publishes `WhisperRecorded` after the save, on the stream that the events catalogue names (add it if missing). Use the Watcher app container from TASK-0916.
2. The gateway session frame consumer maps it to `dm_whisper` and sends it only to sockets whose caller holds `session.control`. Players and spectators never receive it. Check the permission once per socket at admit time and keep it on the socket.
3. Redelivery sends no second frame.
4. Update the events catalogue and the whisper how-to.

## Frontdoor Blackbox Test Plan

- A whisper through the public Watcher route publishes the event (assert on the stream).
- With DM, player and spectator sockets open, the DM socket gets one `dm_whisper` frame and the others get none.
- An unreachable stream answers 503 on the whisper route.

## Definition of Done

- Tests above pass. Docs and CHANGELOG `Added` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0923.md
