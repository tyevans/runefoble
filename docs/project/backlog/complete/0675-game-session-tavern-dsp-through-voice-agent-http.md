---
id: '0675'
title: Game Session Tavern Voice DSP Calls Voice Agent Over HTTP
status: Complete
created: 2026-11-17
dependencies:
- TASK-0491
- TASK-0598
governing_adrs:
- ADR-0007
- ADR-0015
governing_prds:
- PRD-0024
governing_stories:
- US-0047
target_release: 0.9.0
severity: high
source_audits:
- work/0620.md
---

# TASK-0675: Game Session Tavern Voice DSP Calls Voice Agent Over HTTP

## Status
Complete

## Summary
`game_session` imports the voice DSP pipeline from `voice_agent` and runs it in process. This breaks the bounded context boundary (ADR-0007) and the no-in-process-import rule for deployed services (ADR-0015 item 12). This task moves the call to a public HTTP route on `voice_agent`.

## Problem Statement
- `services/game_session/src/game_session/minigame_rules.py:12` imports `from voice_agent.dsp import VoiceDSPPipeline`.
- `apply_tavern_voice_dsp` (lines 134-146) builds the pipeline and returns `conditioned_text`, `active_filters`, and `dsp_config`.
- `services/game_session/src/game_session/minigames.py:253-264` calls it on the drink roll and returns the result as `voice_dsp`.
- The computation does not produce audio. It is text conditioning and filter parameters.

## Documentation & Architecture Review
- ADR-0007: services talk through public contracts. No service imports another service's package.
- ADR-0015 item 12: in-process package imports are a fallback. Remove them from deployed code.
- `docs/how-to/modulate-dm-vocal-npc-presets.md` and `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`: confirm the DSP route names before adding a new one.
- Use the service URL settings from TASK-0624.

## Product & User Story References
- PRD-0024 and US-0047: tavern drinking contests use voice effects for intoxicated players.

## Detailed Specification & Implementation Plan
1. `voice_agent`: add `POST /api/v1/voice/dsp/condition` (new router module). Input: `text`, `filters` (list of strings). Output: `original_text`, `conditioned_text`, `active_filters`, `dsp_config`. No audio. Reuse `VoiceDSPPipeline` inside `voice_agent` only.
2. `game_session`: add `voice_client.py` with an `httpx` client. Base URL from `RUNEFOBLE_VOICE_AGENT_URL`. Timeout from settings.
3. `minigame_rules.apply_tavern_voice_dsp` becomes async. It calls the client. Remove the `voice_agent` import.
4. `minigames.py`: on upstream failure, raise a 503 for the roll route. Do not return a substitute `voice_dsp` value.
5. `services/game_session/pyproject.toml`: remove the `voice_agent` dependency. Add an import-linter rule (TASK-0598 pattern) that forbids `game_session` from importing `voice_agent`.
6. Helm: wire `RUNEFOBLE_VOICE_AGENT_URL` in the game-session deployment (TASK-0624).

## Frontdoor Blackbox Test Plan
- Put a voice-agent double on the network boundary. It returns a fixed `dsp_config`. Drink-roll route through the public API returns `voice_dsp` equal to the double's response.
- Stop the double. The same route returns 503. The response has no `voice_dsp` value.
- Assert HTTP status and body only. The double records the request body (text and filters).

## Definition of Done
- Tests above pass. `rg "from voice_agent" services/game_session/src` returns nothing.
- Import-linter contract passes (`uv run lint-imports`).
- OpenAPI for `voice_agent` lists the new route. `docs/reference/ports-and-endpoints.md` updated.
- Changed files under 500 lines. `uv run pytest` and `make lint` pass.
