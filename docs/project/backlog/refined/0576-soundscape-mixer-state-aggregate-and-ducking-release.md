---
id: '0576'
title: Soundscape Mixer and Session State Held in the Aggregate, With Ducking Released
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.9.0
severity: high
source_audits:
- w2-soundscape.md
---

# TASK-0576: Soundscape Mixer and Session State Held in the Aggregate, With Ducking Released

## Status
Refined

## Summary
Soundscape changes the mixer and master volume without recording an event, keeps the mixer and leitmotif engines in process-local dicts, and generates a random aggregate id per process. Ducking turns on for speech and cues but nothing turns it off on the backend. This task moves all user-visible mixer state into the aggregate, derives the aggregate id from the session id, and releases ducking through an event.

## Problem Statement
- `services/soundscape/src/soundscape/routers/stems.py:60-84` (`POST /stems/volume`) changes `mixer.channel_volumes` without an event. `routers/stems.py:87-160` (`override_mood`) sets `master_volume` and `stem_profile` (w2-soundscape F6).
- `services/soundscape/src/soundscape/dependencies.py:33-35` keeps `_session_to_aggregate`, `_session_mixers`, and `_session_leitmotif_engines` in process memory. `dependencies.py:80` uses a random `uuid4()` aggregate id, so each restart starts a new empty stream for the same session (F6).
- `event_handlers.py:92-95` sets ducking on speech. `routers/cue.py` sets it for cues. Nothing in `src/` clears it except `POST /api/v1/soundscape/duck` (`routers/stems.py:166`). `GET /tension` then reports `is_ducked: true` and `effective_gain` 0.25x (w2-soundscape F3).
- `routers/tension.py:26-67` reads tension from the aggregate and `is_ducked` and `master_volume` from the mixer, so the two can disagree (F6).

## Documentation & Architecture Review
- `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` describes ducking. Verify it. Correct the claim that ducking clears on speech end, unless this task makes it true.
- The UI clears ducking in the browser only (`services/soundscape/ui/src/runefoble-soundscape-controls.ts:73`). The backend must match. The UI change is limited to calling the release route after the timer.

## Product & User Story References
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. Derive the aggregate id from the session id with UUID v5 (namespace constant in `soundscape/ids.py`).
2. Record `ChannelVolumeChanged`, `MasterVolumeChanged`, `StemProfileOverridden`, `DuckingEngaged`, and `DuckingReleased` as aggregate events. Mixer values are rebuilt from events.
3. Speech end and cue end emit `DuckingReleased` through the aggregate. A timer in the owning process is not the source of truth. The duck duration is stored on the event.
4. `GET /tension` reads every field from the aggregate or from one projection.
5. Remove `_session_mixers` and `_session_leitmotif_engines` as sources of truth. Replace the broad `except` (TASK-0561).

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** set master volume through `POST /api/v1/soundscape/stems/override`, restart the app, then `GET /api/v1/soundscape/tension`. Before: default volume. After: the set volume.
- **Fail before, pass after:** post a speech event through the public route, then end speech. `GET /tension` shows `is_ducked == false`. Before: true.
- **Fail before, pass after:** the aggregate id is the same across two process starts for the same session (observed through the stream).
- Public routes only.

## Definition of Done
1. No process-local dict holds mixer state (grep). Aggregate id is deterministic.
2. Three tests above pass. Events registered and documented.
3. `uv run pytest` and `make health-check` pass. Files under 500 lines.
4. How-to and reference docs corrected. `CHANGELOG.md` entry.
