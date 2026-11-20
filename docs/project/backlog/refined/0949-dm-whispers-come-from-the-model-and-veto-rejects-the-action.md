---
id: '0949'
title: DM Whispers Come from the Language Model, and a Veto Stops the Action
status: Refined
created: 2026-11-19
dependencies:
- '0943'
- '0948'
governing_adrs:
- ADR-0002
- ADR-0014
- ADR-0015
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0017-human-dm-veto-and-narrative-copilot-whispers
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0949: DM Whispers Come from the Language Model, and a Veto Stops the Action

## Status

Refined. Removes the invented whispers and connects the veto button to a real route. Covers PRD-0025 "The DM sees invented whispers, and the Veto button does nothing."

## Summary

The DM bar shows three whispers that the code wrote in advance. The whisper generator also writes fixed text. The veto button sends an event that no code receives. This task removes the fixed text. Whispers come from the narration port. When no model is configured, the bar says so. The veto button calls the veto route, and the vetoed action does not run.

## Problem Statement

- `services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts:31-46`: the `whispers` property starts with three invented whispers (`whisp-1` to `whisp-3`).
- `services/the_watcher/src/the_watcher/copilot_whispers.py:34-84`: `build_default_whispers` writes three fixed texts.
- `services/the_watcher/src/the_watcher/copilot_whispers.py:116`: `list_whispers` seeds the log with those texts when the log is empty.
- `services/the_watcher/src/the_watcher/copilot_whispers.py:142-156`: `generate_whispers` records the same fixed texts (call at `:151`). No narration port is called.
- `services/the_watcher/src/the_watcher/adapters/worker_engines.py:99-129`: the worker narrator exists. It returns `narrative` and `suggested_dm_prompts`.
- `services/the_watcher/src/the_watcher/adapters/heuristic_engines.py` (removed) (deleted by TASK-0943): the old narrator raised 503 with no text.
- `services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts:137-141`: `handleVeto` dispatches `action-vetoed`. A search of `frontend/src` and `services/*/ui/src` found no listener for `action-vetoed`.
- `services/the_watcher/ui/src/runefoble-dm-whisper-bar.ts:125-131`: `handleApprove` dispatches `action-approved`. No listener exists either. This is the same gap for approve. It is out of scope here (see the Detailed Specification, step 7).
- `services/the_watcher/src/the_watcher/routers/copilot/actions.py:29-41`: the veto route exists. It requires DM permission (`require_dm`).
- `gateway/api/src/gateway_api/routers/watcher_proxy_dm.py:161-167`: the gateway veto route exists.
- `frontend/src/components/plugins/plugin_registry.ts:104`: the bar is registered as a plugin for the `sidebar-tool` slot. The registry entry has no session or campaign id. The plugin host (`frontend/src/components/plugins/runefoble-plugin-slot.ts:101-107`) creates the sandbox. This report did not trace how the host sets properties. TASK-0949 must check it first.
- No UI code calls `GET /api/v1/watcher/whispers` (`watcher_proxy_dm.py:99-103`), and no UI code calls `POST /api/v1/watcher/actions/propose` (`watcher_proxy_dm.py:140`).
- `services/the_watcher/src/the_watcher/routers/copilot/whispers.py:64-73`: the generate route exists.

## Documentation & Architecture Review

- ADR-0002: The Watcher proposes. Players and the DM keep the veto.
- ADR-0015 Context item 4: no invented output. A missing engine is a 503 with a clear state.
- ADR-0022 (b) and (c): the model writes the narration. A failure returns 503. No fallback text.
- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: update it. It describes the whisper and veto behaviour.
- `docs/explanation/the-watcher-autonomous-dm.md`: check the veto description.

## Product & User Story References

- PRD-0025, checkable outcome 1 (the whisper and veto steps) and "What good looks like" item 6.
- US-0017 (human DM veto and narrative co-pilot whispers).

## Detailed Specification & Implementation Plan

1. Remove the three invented whispers from `runefoble-dm-whisper-bar.ts:31-46`. The default is an empty list.
2. Remove the seed in `list_whispers` (`copilot_whispers.py:116`). An empty log returns an empty list.
3. Delete `build_default_whispers` (`copilot_whispers.py:34-84`) and its callers. Remove the old tests of the fixed text. Do not keep an alias.
4. `generate_whispers` calls the narrator port that TASK-0943 selects. It builds a `DMGuidanceRequest` from the session and the scene state. Each narrative in the result becomes one whisper. Its `whisper_type` is `narration`, and its metadata holds `source` from the result.
5. When the narrator port is `none`, the generate route returns 503 with the backend name `narration`. The bar shows the text "No language model is configured for whispers." The bar shows no whisper.
6. The bar loads its whispers from `GET /api/v1/watcher/whispers` through the gateway. It loads them when it receives its session and campaign ids.
7. Veto: the host of the bar handles `action-vetoed`. It posts `{ session_id, campaign_id, action_id, reason }` to `POST /api/v1/watcher/veto` through the gateway. A 200 reply marks the pending action as vetoed in the bar. The pause window ends without a board change. Approve (`action-approved`, `runefoble-dm-whisper-bar.ts:125-131`) is out of scope for this task. Record it as a follow-up.
8. Session and campaign ids: the plugin registry entry must receive them. Set them in the registry entry or in the host that mounts the bar. Choose one, and note it in the record of the task.
9. Pending action setup for the end-to-end scenario: no UI control proposes an action. The scenario uses the public route `POST /api/v1/watcher/actions/propose` with the DM's token. DoR item 8 allows public REST setup. Record this as a decision in the test file header, and keep the rest of the scenario UI-only.

## Frontdoor Blackbox Test Plan

- Pytest through the gateway (`tests/test_blackbox_dm_whispers_model.py`, new, and `tests/test_blackbox_dm_copilot_whispers.py` updated):
  - A new session returns an empty whisper list (no seed).
  - Generate with the narrator set to `none`: HTTP 503 with backend `narration`. No whisper is recorded.
  - Generate with the worker live on a loopback URL: each whisper has `whisper_type` `narration` and `source` `llm`. The test uses the real worker, reached through a live loopback OpenAI-compatible endpoint that the test starts.
  - Propose an action, then veto it as the DM: the veto returns 200 with status `vetoed`. After the pause window, the board token has not moved. A player's veto attempt returns 403.
- Playwright scenario `e2e/features/dm_whispers_and_veto.feature`:
  - The DM opens the session. The whisper bar shows "No language model is configured for whispers." when the narrator is `none`. The bar shows no invented text.
  - With the narrator live: the DM sees a whisper whose text came from the model.
  - The DM clicks Veto on a pending action. The bar shows "vetoed". The token does not move after the pause window.
- Storybook stories for the bar: empty, no model, whispers, pending action, vetoed. Zero console errors.

## Definition of Done

- Every test in the plan passes. The Playwright scenario passes on Kind with no backdoor state.
- `grep -rn "whisp-1\|build_default_whispers" services frontend/src` returns no match.
- `grep -rn "action-vetoed" frontend/src services/*/ui/src` shows a listener.
- Approve is recorded as a follow-up in the task's Done note.
- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md` is updated.
- A CHANGELOG `Fixed` entry under `[Unreleased]` says that the DM whispers come from the model and that the veto works.
- Every file the task touches stays under 500 lines. The bar file is 348 lines today. Check the size after the change.

## Audit Provenance

- Severity: high (PRD-0025 release blocker; human veto authority in ADR-0002).
- Source audits: `.audit/research/r1-watcher-llm.md` ("No LLM: copilot whispers are canned text"; "S8"), `.audit/research/r1-core-journeys.md` (section 4, item 4: the whisper bar and the veto journey).
