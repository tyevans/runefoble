---
id: '0946'
title: Push to Talk Captures an Utterance and Uploads It for Transcription
status: Complete
created: 2026-11-19
dependencies:
- '0945'
governing_adrs:
- ADR-0004
- ADR-0013
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

# TASK-0946: Push to Talk Captures an Utterance and Uploads It for Transcription

## Status

Complete

## Summary

Push to Talk only flips a flag, and it draws a level meter. No code sends audio. The element also shows a "WebRTC Live" badge that is false. This task makes Push to Talk hold-to-talk. The element records the utterance, encodes it as WAV at 16 kHz mono, and sends it through the gateway to `POST /api/v1/voice/transcribe`. The false badge and the simulated states are removed.

## Problem Statement

- `services/voice_agent/ui/src/runefoble-voice-controls.ts:153-162`: `_handleToggle` dispatches a `voice-toggle` event. It sends no audio.
- `services/voice_agent/ui/src/runefoble-voice-controls.ts:79-96`: `startAudio` connects the microphone to an analyser only. The stream is not recorded.
- `services/voice_agent/ui/src/runefoble-voice-controls.ts:177`: the text `● WebRTC Live` is shown. No WebRTC connection exists for the Push to Talk button.
- `services/voice_agent/ui/src/runefoble-voice-controls.ts:20`: the `simulated` property. A simulated render loop draws a fake level.
- `services/voice_agent/ui/src/runefoble-voice-controls.ts:210-217`: the button label is "Push to Talk" or "Streaming (Mute)". It is a toggle, not hold-to-talk.
- `gateway/api/src/gateway_api/routers/voice_proxy.py:19-81`: no route for `/api/v1/voice/transcribe`.
- `gateway/api/src/gateway_api/proxy_table.py:78`: the default proxy timeout is 5.0 s. The transcribe route runs STT and the Watcher. Its timeout must be higher.
- `services/voice_agent/src/voice_agent/routers/transcribe.py:57-117`: the route exists and needs a caller that speaks for the speaker (`:68`). It publishes `PlayerSpokeEvent` before it forwards (`:92`).
- `services/voice_agent/src/voice_agent/models.py:89-97`: `TranscribeRequest` takes `audio_base64`, `transcript`, `speaker_id`, `session_id`, `campaign_id`.
- `services/voice_agent/src/voice_agent/vad.py:23`: `parse_audio_data` reads WAV and raw PCM. The server accepts a WAV upload.

## Documentation & Architecture Review

- ADR-0015 (c): the speaker's own bearer is forwarded. The gateway holds no state and adds no permission check.
- ADR-0015 Context item 4: a failed upload shows the error. The element never shows a transcript that it did not receive.
- ADR-0022 (e): no latency target is claimed here. TASK-0947 measures it.
- `docs/reference/ui-transport.md`: the shared HTTP client for browser calls.
- `docs/reference/ports-and-endpoints.md`: add the gateway row for the transcribe route.

## Product & User Story References

- PRD-0025, "Speech does nothing for the game", and "What good looks like" item 4.
- US-0001.

## Detailed Specification & Implementation Plan

1. Gateway row: in `gateway/api/src/gateway_api/routers/voice_proxy.py`, add a `ProxyRoute` for `POST /api/v1/voice/transcribe`. Set `body="json"`, `principal=True`, and `timeout` above the owner's worst case: STT, then the Watcher intent (2 s), the board read (2 s) and the proposal (2 s). Use 10 s. Document the number in the row comment, as `watcher_speech_proxy.py:17-19` does.
2. Capture: make the Push to Talk button hold-to-talk. Pointer down starts a capture. Pointer up, leave or cancel stops it. The Space key down and up do the same for keyboard users.
3. Record with `MediaRecorder` on the existing `getUserMedia` stream. When recording stops, decode the blob with `AudioContext.decodeAudioData`. Resample to 16 kHz mono with `OfflineAudioContext`. Encode the samples as PCM 16-bit WAV with a new pure function in `services/voice_agent/ui/src/wav-encoder.ts`.
4. The element emits `voice-utterance` with `{ audioBase64 }`. It does not know the session. The App Shell handler posts `{ speaker_id, speaker_name, session_id, campaign_id, audio_base64 }` to the gateway route. The speaker id is the signed-in user id.
5. Show the returned `transcript` and any `watcher_error` in the element. Show a failed upload as an error. Do not hide it.
6. Remove the `● WebRTC Live` text (`:177`), the `simulated` property (`:20`) and every branch that draws a fake level. Keep the analyser for the level meter, which is real input.
7. Do not change the duplex controls (`runefoble-voice-duplex-controls.ts`). They are out of scope for release one.

## TASK-0942 Note (2026-11-19)

Since TASK-0942, The Watcher returns 422 for a spoken or typed move without `from_x` and `from_y`, and it never moves from (0, 0). The caller must send `token_id`, `from_x`, `from_y`, `grid_cols` and `grid_rows` for the speaker's token. The voice agent forward (`services/voice_agent/src/voice_agent/routers/transcribe.py`) sends none of these today. Read them from the board state that the App Shell holds, and send them with the command.

## Frontdoor Blackbox Test Plan

- Pytest through the gateway (`tests/test_blackbox_gateway_voice_transcribe.py`, new): a valid WAV body returns 200 with the transcript and `source` `audio`. A body with no audio and no transcript returns 422. A request without a bearer returns 401. A speaker that is not the caller returns 403. The test uses the live voice_agent and the STT engine that the test settings select. No substitute transcript is allowed in any deployed environment (ADR-0015 Context item 4).
- Vitest for `wav-encoder.ts`: the header fields, the length, and the sample scaling for a known input.
- Storybook stories for the element: idle, holding, sending, transcript shown, error. Zero console errors.
- Playwright: no new scenario in this task. TASK-0947 owns the end-to-end scenario.

## Definition of Done

- Every test in the plan passes, with `uv run pytest` and `pnpm` test runs for the named files.
- `grep -rn "WebRTC Live" services/voice_agent/ui/src` returns no match.
- `grep -rn "simulated" services/voice_agent/ui/src/runefoble-voice-controls.ts` returns no match.
- `docs/reference/ports-and-endpoints.md` lists the gateway row.
- The Storybook stories build with zero console errors.
- A CHANGELOG `Added` entry under `[Unreleased]` says that Push to Talk sends audio for transcription.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 release blocker).
- Source audits: `.audit/research/r1-voice-path.md` (section 1, steps 1 to 4; section 7, slice S2).
