---
id: '0947'
title: The Spoken Move Runs End to End with a Fake Microphone, and Its Latency Is Measured
status: Refined
created: 2026-11-19
dependencies:
- '0946'
governing_adrs:
- ADR-0014
- ADR-0015
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0001-player-commands-board-via-voice
target_bc: voice_agent
target_release: 1.0.0
---

# TASK-0947: The Spoken Move Runs End to End with a Fake Microphone, and Its Latency Is Measured

## Status

Refined. Closes the voice loop with a real speech-to-text engine. It supplies the first latency number for ADR-0022 (e).

## Summary

No end-to-end test covers voice. This task adds a Playwright scenario that speaks a move into a fake microphone. The browser captures the speech, the real speech-to-text engine transcribes it, the Watcher stages the ghost, and the player confirms it. The scenario prints the time from the release of Push to Talk to the ghost banner. The scenario is tagged `@requires-stt`, so the default run skips it.

## Problem Statement

- `playwright.config.ts:44-62`: the projects are `chromium`, `firefox` and `webkit`. The chromium project grants clipboard permissions only (`:47`). It has no `launchOptions.args`, so it has no fake device.
- `e2e/features/`: no feature file covers voice. A search for "voice", "microphone" and "push to talk" in `e2e/` returned no match.
- `e2e/fixtures/`: the directory does not exist.
- `Makefile:99`: the voice image installs `espeak-ng`. Its TTS engine is the only one that the speech settings accept (`services/voice_agent/src/voice_agent/speech_settings.py:33-34`). The developer host can use `espeak-ng` to make a fixture WAV.
- `docs/marketing.md:81`: "The speech targets are not measured." No latency test covers the release path. The only latency tests cover the grammar (`tests/test_speech_to_intent.py:146-172`) and a test double STT (`tests/test_blackbox_streaming_whisper_e2e.py`).
- `docs/how-to/test-user-flows-with-playwright-bdd.md` and `docs/reference/e2e-harness.md`: update both for the new project and tag.

## Documentation & Architecture Review

- ADR-0014: each user flow is a Gherkin scenario in Playwright, with UI-only setup (Hard Invariant 7).
- ADR-0015 Context item 4: no substitute transcript. The fixture audio must reach the real engine. The scenario must not pass when the engine is down.
- ADR-0022 (e): the latency target is stated only after this measurement. This task reports the number. It does not set a target.

## Product & User Story References

- PRD-0025, checkable outcomes 1 and 2.
- US-0001.

## Detailed Specification & Implementation Plan

1. Fixture: create `e2e/fixtures/audio/move-two-squares-west.wav`. Make it with a Makefile target, `e2e-speech-fixture`, that runs `espeak-ng -w` on the developer host. Commit the WAV. Record the phrase in a comment next to the target.
2. Playwright project: add `voice-chromium` to `playwright.config.ts`. It uses the Chromium device and sets:
   - `permissions: ['clipboard-read', 'clipboard-write', 'microphone']`
   - `launchOptions.args`: `--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream`, and `--use-file-for-fake-audio-capture=<absolute path of the WAV>%noloop`. Compute the path from `__dirname`.
   - `grep: /@requires-stt/`.
   Set the `chromium` project to `grepInvert: /@requires-stt/`. The default run then skips the tagged scenario.
3. Scenario `e2e/features/voice_spoken_move.feature`, tagged `@requires-stt`:
   - Background: the same UI-only setup as `session_lobby_and_vtt.feature`, with a launched session and a battlemap set up.
   - Valeros holds Push to Talk and releases it. The fake device plays the WAV once.
   - The ghost banner appears on both screens, and names a cell two squares west of the token.
   - Valeros clicks Confirm. The token moves on both screens.
4. Measurement: the step records the time at the Push to Talk release (the Node clock, before the release action returns) and the time when the ghost banner first becomes visible. Print the difference in milliseconds as a test annotation and in the console log. Note in the output that the figure includes Playwright overhead.
5. Confirm the Chromium flags on the first run. The flags come from public sources, not from this repository. If a flag is refused, record the Chromium version and the fix in the step comment.
6. Run: add a Makefile target `test-e2e-voice` that runs only the `voice-chromium` project. It needs the STT engine. When the engine is down, the target fails. Keep the tagged scenario out of the default CI job.

## Frontdoor Blackbox Test Plan

- Playwright scenario `voice_spoken_move.feature` (above). It uses the browser microphone path, the gateway transcribe route, the live Watcher, the board socket and the confirm button. No backdoor or direct database access.
- Negative scenario in the same feature, tagged `@requires-stt`: the STT engine is unavailable. Use the service fault helper in `e2e/support/service_faults.ts`. The transcript is not shown. The bar shows the error.
- The default `make test-e2e` run excludes the tag, and it passes.

## Definition of Done

- The tagged scenario passes on Kind with the real speech-to-text engine. It passes twice in a row.
- The default e2e run passes with the tag excluded.
- The printed latency is recorded in the task's Done note as a measured value. The record does not set a target.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` and `docs/reference/e2e-harness.md` describe the new project, the tag and the fixture target.
- The fixture WAV is committed. Its phrase and the make target are documented.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 checkable outcomes 1 and 2).
- Source audits: `.audit/research/r1-voice-path.md` (section 5, section 7 slices S3 and S4).
