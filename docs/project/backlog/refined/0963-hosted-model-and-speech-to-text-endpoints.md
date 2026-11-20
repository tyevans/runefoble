---
id: '0963'
title: Hosted Language Model, Embedding, and Speech-to-Text Endpoints Come from Values
status: Refined
created: 2026-11-19
dependencies:
- '0948'
- '0959'
- '0933'
governing_adrs:
- ADR-0015
- ADR-0022
governing_prds:
- PRD-0025
governing_stories: []
target_bc: inference_worker
target_release: 1.0.0
---

# TASK-0963: Hosted Language Model, Embedding, and Speech-to-Text Endpoints Come from Values

## Status

Refined. Release One hosting slice 12 (PRD-0025, "What it costs at scale": the speech-to-text engine and the language model run on a GPU host outside the cluster). Writer C added dependency `0933`: the readiness probes named here need the `/readyz` change from that record.

## Summary

Point the hosted release at operator-run endpoints for the language model, the embeddings, and the speech-to-text engine. Set each one with a value. Add a readiness check that reports `503` when a configured endpoint does not answer. The chart does not deploy a model server, and no fallback runs.

## Problem Statement

- `deployments/helm/runefoble/values.yaml:459-476` (inference worker): `backend: openai_compatible` (`values.yaml:471`) and `openaiCompatibleBaseUrl: ""` (`values.yaml:474`). The template renders the base URL (`templates/inference-worker.yaml:32`) and the model (`:33-35`).
- `values.yaml:470` sets the inference readiness path to `/healthz`. `services/inference_worker/src` contains no `/readyz` route (search found none). The worker checks the engine at start-up only (`values.yaml:465-466`).
- `values.yaml:355-368` (voice agent): the default engine is `faster-whisper` (`values.yaml:358`) with a 1 Gi model cache (`values.yaml:366-368`). The model is copied in by hand (`Makefile:135-140`, `kubectl cp`).
- `services/voice_agent/src/voice_agent/speech_settings.py:24` already accepts `whisper-cpp`. `speech_settings.py:37-41` requires `RUNEFOBLE_VOICE_STT_BASE_URL` for it. `services/voice_agent/src/voice_agent/whisper_cpp_transcriber.py:60` defines `check_ready`. The chart sets the URL at `templates/services.yaml:81`.
- `values.yaml:354` sets the voice-agent readiness path to `/healthz`. `services/voice_agent/src/voice_agent/main.py:107` answers `/healthz` only.
- `values.yaml:379-387` (embeddings): base URL, model, and dimension are empty. Start-up names each missing setting (comment at `values.yaml:379-380`). The API key comes from a Secret (`values.yaml:385-387`).
- `Makefile:184-188` (`deploy-remote-worker`) uses a development LAN host. Hosted values must not use it.

## Documentation & Architecture Review

- ADR-0015 (b) and Context item 4 ("fallbacks hide failures"): when an endpoint does not answer, the service reports it and does not return a substitute.
- ADR-0022 (`docs/project/adrs/accepted/adr-0022-grammar-first-voice-intent-routing.md`), line 29 and line 32: the language model receives only transcripts that the grammar returns as `narrative`. When no model is configured, The Watcher answers "not understood". When the model call fails, The Watcher returns `503`. It never sends the transcript to another engine.
- `docs/how-to/add-an-engine-port-adapter.md`: an unavailable engine returns `503`. Follow that rule.
- `docs/how-to/test-cross-service-calls-with-live-upstreams.md`: the test pattern for a live loopback upstream. Use it for the model and STT tests. Do not mock the client.
- `docs/reference/inference-worker-response-contract.md`: the response contract of the worker. Check it after the readiness change.

## Product & User Story References

- PRD-0025, "What it costs at scale" (GPU host outside the cluster) and "What this does not do" (no latency target until measured).
- PRD-0025, Checkable Outcome 2 (the spoken move scenario) depends on the STT endpoint.
- No user story for the hosting setup.

## Detailed Specification & Implementation Plan

1. Language model:
   - The hosted example sets `services.inferenceWorker.openaiCompatibleBaseUrl` (input D10), `openaiCompatibleModel`, and the API key Secret (record 0948).
   - Set the inference readiness path to `/readyz` (record 0933). The readiness check calls the configured engine. It returns `503` when the endpoint does not answer. The worker code change belongs to this record. Check first whether the 0948 settings already expose an engine check (the 0948 record owns those settings).
2. Speech-to-text. Choose one option (input D10b):
   - Option A (default): `services.voiceAgent.sttEngine: whisper-cpp` and `sttBaseUrl` set to the operator's whisper.cpp HTTP endpoint on the GPU host. The model cache is not rendered for this engine (`voice-agent-model-cache.yaml:1` renders only for `faster-whisper`). The copy step in `Makefile:135-140` is not used. The voice-agent readiness check calls `check_ready` on the transcriber. It returns `503` when the endpoint does not answer. Set the readiness path to `/readyz` (record 0933).
   - Option B: keep `faster-whisper` on CPU in the cluster. A model-delivery Job fetches the model from a value URL into `modelCache`. This replaces `Makefile:135-140`. The Job needs egress to the model host (record 0962).
3. Embeddings. The hosted example sets `RUNEFOBLE_EMBEDDING_BASE_URL`, `RUNEFOBLE_EMBEDDING_MODEL`, and `RUNEFOBLE_EMBEDDING_DIMENSION` (input D10c). The key comes from the Secret named in `embeddingApiKeySecret` (record 0959).
4. Do not use the development LAN host. Hosted values hold only the operator's URLs.
5. The hosted guard (0955) fails when `openaiCompatibleBaseUrl` or an embedding base URL is empty, or when `sttEngine` is `faster-whisper` and the model cache is not set.

Rules for this record:
- No substitute model output. A missing model returns `503`.
- The URLs are values, not code constants.

### Inputs (user decisions)

- D10: GPU host and its base URL for the language model, with the model name.
- D10b: speech-to-text option (A or B in section 2). Default: A.
- D10c: embedding endpoint base URL, model name, and vector width.

## Frontdoor Blackbox Test Plan

Render tests in `tests/test_blackbox_helm_voice_stt.py` (extend) and a new `tests/test_blackbox_helm_hosted_endpoints.py`:
- Hosted render, option A: voice-agent has `RUNEFOBLE_VOICE_STT_ENGINE` `whisper-cpp` and `RUNEFOBLE_VOICE_STT_BASE_URL` with the value. No model-cache PersistentVolumeClaim for voice-agent.
- Hosted render: the inference worker has the base URL and model values. Its readiness path is `/readyz`.
- Hosted render: the campaign-lore pod has the three embedding settings set and non-empty.
- Guard: an empty base URL fails the render with the key name.

Live tests (new, `tests/test_blackbox_inference_hosted_readiness.py`, on live loopback upstreams per the how-to):
- Start a loopback HTTP server that answers the OpenAI-compatible API. Point the inference worker at it. `/readyz` returns `200`.
- Stop the loopback server. `/readyz` on the worker returns `503`. A narration request returns `503`, with no text.
- The same pattern for whisper.cpp: `/readyz` on voice-agent returns `503` when the loopback server is down.

Playwright (UI only, in the 0964 smoke job when the endpoint is set up): with the loopback server stopped, a narrative utterance shows the error state that ADR-0022 defines. It never shows a canned reply.

## Definition of Done

- Render and live tests pass. `helm lint` and `helm template` pass.
- `docs/reference/inference-worker-response-contract.md` and `docs/reference/platform-services.md` describe the hosted endpoints and the `503` rule.
- D10, D10b, and D10c are recorded in `docs/reference/hosted-profile.md`.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (no hosted language model or speech-to-text path exists).
- Source audits: `.audit/research/r1-hosting.md`, sections 3, 8, 9 and 11 (D10). Lines were checked against `main` at `33885a70`. The research cites `Makefile:87-91` for the development GPU host; the target is at `Makefile:184-188`.
