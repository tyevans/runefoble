---
id: '0948'
title: The Inference Worker Takes Its Hosted Settings from Helm, and the Watcher Budgets Are Configurable
status: Refined
created: 2026-11-19
dependencies:
- '0943'
governing_adrs:
- ADR-0005
- ADR-0015
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories: []
target_bc: inference_worker
target_release: 1.0.0
---

# TASK-0948: The Inference Worker Takes Its Hosted Settings from Helm, and the Watcher Budgets Are Configurable

## Status

Refined. Infrastructure and documentation slice that supports the hosted release. It follows TASK-0943, which fixes the engine settings.

## Summary

The worker reads its API key, Ollama URL, temperature, token limit and timeout from its settings. The Helm template does not pass them, so a deployed worker cannot use them. The Watcher's timeouts are fixed in code. This task passes the settings through Helm, makes the Watcher budgets configurable, keeps the local secret file out of git, and corrects the stale documentation.

## Problem Statement

- `services/inference_worker/src/inference_worker/config.py:45-63`: the settings `openai_api_key`, `ollama_base_url`, `ollama_model`, `temperature` (default 0.7), `max_tokens` (default 512) and `timeout_seconds` (default 30.0).
- `deployments/helm/runefoble/templates/inference-worker.yaml:23-39`: the env list sets the backend, the OpenAI base URL and the optional model. It sets no API key, no Ollama value, no temperature, no token limit and no timeout.
- `deployments/helm/runefoble/values.yaml:459-476`: the `inferenceWorker` block. `openaiCompatibleBaseUrl` is empty at `:474`.
- `services/the_watcher/src/the_watcher/adapters/worker_engines.py:44`, `:84` and `:119`: the timeouts are fixed at 2.0 s (intent), 10.0 s (stand-in) and 10.0 s (narration).
- `services/the_watcher/src/the_watcher/worker_client.py`: the timeout is passed in. It is not read from settings.
- `services/the_watcher/src/the_watcher/board_client.py:28`: the board read has a fixed 2.0 s timeout. `services/the_watcher/src/the_watcher/board_preview.py:17`: the proposal has a fixed 2.0 s timeout.
- `gateway/api/src/gateway_api/routers/watcher_speech_proxy.py:17-19`: the gateway waits 5.0 s for speak-and-act. The Watcher worst case is 2.0 s (intent) plus 2.0 s (board read) plus 2.0 s (proposal) = 6.0 s. The gateway timeout is shorter than the worst case.
- `services/inference_worker/src/inference_worker/config.py:16`: the worker reads `.env.worker`. `.gitignore` does not list that file. A search of `.gitignore` for `worker` returned no match.
- `docs/marketing.md:76` and `:79`: both cite TASK-0509 as the blocker. TASK-0509 is a duplex task. The citation is wrong.
- `docs/marketing.md:102`: "The LLM provider path is not wired." The path is wired for narration and stand-ins today. The citation of TASK-0448 and TASK-0449 is out of date.
- `docs/how-to/add-an-engine-port-adapter.md:5` and `:157`, and code comments in `services/inference_worker/src/inference_worker/api.py:46`, `services/inference_worker/src/inference_worker/model_output.py:25`, `services/inference_worker/src/inference_worker/config.py:77` and `services/the_watcher/src/the_watcher/ports.py:4`: they cite "ADR-0015 decision 4". ADR-0015 has no decision 4. The rule is Context item 4.
- `docs/project/backlog/proposed/0448-watcher-pluggable-llm-inference-provider-backend.md` and `docs/project/backlog/proposed/0449-watcher-intent-middleware-pipeline-and-tracing.md`: superseded by TASK-0943 and this task. They need a note.

## Documentation & Architecture Review

- ADR-0005: Helm values drive the deployed settings. A value is set in `values.yaml` and read by a template.
- ADR-0015 (e): the service credential and any API key come from a Kubernetes Secret, not from a value in the chart.
- ADR-0015 Context item 4: a missing key stops the worker at start-up. A default must not fill the gap.
- `docs/reference/platform-services.md`: update the table of settings for the worker and the Watcher.
- `docs/how-to/add-an-engine-port-adapter.md`: fix the citation.

## Product & User Story References

- PRD-0025, "What it costs at scale" and the hosted release settings. No user story.

## Detailed Specification & Implementation Plan

1. Helm values: under `inferenceWorker` in `values.yaml`, add `openaiApiKeySecret` with `name` and `key` (both empty by default), `ollamaBaseUrl`, `ollamaModel`, `temperature` (0.7), `maxTokens` (512) and `timeoutSeconds` (30). The defaults match the worker defaults.
2. Helm template `inference-worker.yaml`: add the env entries `RUNEFOBLE_WORKER_OPENAI_API_KEY` (from `secretKeyRef` when `openaiApiKeySecret.name` is set), `RUNEFOBLE_WORKER_OLLAMA_BASE_URL`, `RUNEFOBLE_WORKER_OLLAMA_MODEL`, `RUNEFOBLE_WORKER_TEMPERATURE`, `RUNEFOBLE_WORKER_MAX_TOKENS` and `RUNEFOBLE_WORKER_TIMEOUT_SECONDS`. Emit the Ollama entries only when their values are set.
3. Watcher budgets: add three fields to `WatcherEngineSettings` (`services/the_watcher/src/the_watcher/engine_selection.py`):
   - `RUNEFOBLE_WATCHER_INTENT_TIMEOUT_S`, default 2.0
   - `RUNEFOBLE_WATCHER_STAND_IN_TIMEOUT_S`, default 10.0
   - `RUNEFOBLE_WATCHER_NARRATION_TIMEOUT_S`, default 10.0
   Each has a positive bound. Pass them to the adapters. Remove the literals at `worker_engines.py:44`, `:84` and `:119`.
4. Gateway budget: the gateway speak-and-act timeout (`SPEAK_AND_ACT_TIMEOUT_S`) must be greater than the sum of the intent budget, the board read budget and the proposal budget. Set it to 8.0 s, and set the Watcher's board read and proposal budgets from settings too. Add the rule to the module comment.
5. Helm: set the three Watcher budgets in the `the_watcher` env block of `values.yaml`, next to `RUNEFOBLE_WATCHER_ENGINE` (now the three engine settings from TASK-0943).
6. `.gitignore`: add `.env.worker`.
7. Documentation fixes:
   - `docs/marketing.md:76` and `:79`: replace TASK-0509 with the voice-loop tasks, TASK-0942 to TASK-0947.
   - `docs/marketing.md:102`: state the paths that are wired today, and name TASK-0943 and TASK-0948 as the work done. Remove the blocking citation of TASK-0448 and TASK-0449.
   - Replace "ADR-0015 decision 4" with "ADR-0015 Context item 4" in the files listed above.
8. Add a note to `docs/project/backlog/proposed/0448-*.md` and `0449-*.md` that TASK-0943 and TASK-0948 replace their scope. Do not move them.

## Frontdoor Blackbox Test Plan

- Helm: `helm template` renders the worker with the API key from the named Secret when `openaiApiKeySecret.name` is set, and without it when it is empty. It renders the temperature, token limit and timeout values. Use `tests/test_blackbox_helm_inference_worker.py` (new), which reads the rendered manifest.
- Worker: a settings test through the process env. The worker reads the new variables. A blank key stops the worker at start-up.
- Watcher: a live loopback worker that answers slowly. A call with the intent budget set to 0.5 s returns 503 within the configured budget. The default value keeps the 2.0 s behaviour.
- Gateway: a speak-and-act call where the Watcher takes 5.5 s returns 200 under the new 8.0 s gateway timeout. Use the live Watcher upstream.
- Documentation: a check that `grep -rn "ADR-0015 decision 4" docs services` returns no match in the listed files.

## Definition of Done

- Every test in the plan passes. `helm lint` and `helm template` pass for the umbrella chart.
- `.env.worker` is in `.gitignore`. `git check-ignore .env.worker` prints the path.
- `platform-services.md` lists the new worker and Watcher settings.
- The documentation fixes in step 7 are applied. The notes in step 8 are added.
- A CHANGELOG `Changed` entry under `[Unreleased]` names the new settings and the gateway timeout.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: medium (hosted release settings; stale documentation).
- Source audits: `.audit/research/r1-watcher-llm.md` ("Hosted release settings", "S5", "S6", "S7"), `.audit/research/r1-voice-path.md` (section 4, TASK-0509 citation).
