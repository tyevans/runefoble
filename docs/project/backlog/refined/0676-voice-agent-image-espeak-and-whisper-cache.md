---
id: '0676'
title: Voice Agent Image Ships espeak-ng and a Speech Model Cache
status: Refined
created: 2026-11-17
dependencies:
- TASK-0620
- TASK-0601
governing_adrs:
- ADR-0005
- ADR-0015
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.9.0
severity: high
source_audits:
- work/0600.md
- work/0601.md
---

# TASK-0676: Voice Agent Image Ships espeak-ng and a Speech Model Cache

## Status
Refined. Created from the discovered-defect triage of round 1 (2026-11-17).

## Summary
The voice agent needs two runtime assets that the image does not provide. The espeak-ng binary runs the TTS path. The faster-whisper model downloads on first use. In a cluster without internet access, TTS returns 503 and the first transcription fails or stalls.

## Problem Statement
- `services/voice_agent/src/voice_agent/espeak_synthesizer.py` runs the `espeak-ng` binary. `deployments/docker/python-service.Dockerfile` (TASK-0620) installs no system packages for `voice_agent`. The Helm image is `runefoble/voice-agent:0.1.0` (`values.yaml`).
- Without the binary, `POST /api/v1/voice/synthesize` returns 503 (`speech_synthesis_error_body`).
- faster-whisper downloads its model on first use. No model cache volume or pre-fetch step exists in the chart.

## Documentation & Architecture Review
- `docs/reference/platform-services.md`: list the system packages and the model cache path.
- ADR-0005: image and runtime settings belong in the Helm chart and the Dockerfile. Do not install packages at pod start.
- ADR-0015: a missing dependency fails the readiness check. It does not degrade silently.

## Product & User Story References
- PRD-0020 and US-0060: the voice pipeline must work in the deployed cluster.

## Detailed Specification & Implementation Plan
1. `deployments/docker/python-service.Dockerfile`: add a build argument `SYSTEM_PACKAGES`. The voice-agent build passes `espeak-ng`. Other services pass nothing.
2. Set `WHISPER_MODEL_DIR` (or the existing setting) to a path on a volume. In Helm, mount a PVC for `voiceAgent`. Add a values key for the model name.
3. Add a readiness check that fails when `espeak-ng --version` fails or the model directory is empty and download is disabled. Use the existing `/healthz` route.
4. Add a `make` target that pre-fetches the model into the cache for Kind (for example `make voice-model-cache`).
5. Update `docs/reference/platform-services.md` and the TTS note in `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`.

## Frontdoor Blackbox Test Plan
- Build the voice-agent image with `make images`. Run the container with the chart. `POST /api/v1/voice/synthesize` returns HTTP 200 and a WAV payload.
- Send a short audio fixture to `POST /api/v1/voice/transcribe` in the cluster with network disabled to the model host. The request uses the pre-fetched model and returns a transcript.
- Check `GET /healthz` reports not-ready when the model cache is removed.

## Definition of Done
- Tests above pass. `helm lint` and `helm template` pass.
- `docs/reference/platform-services.md` updated.
- Changed files under 500 lines. `make lint` passes.
