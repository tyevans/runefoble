---
id: '0608'
title: Inference Worker Stand-In Guardrails Contract Matches The Watcher
status: Complete
created: 2026-11-17
dependencies:
- TASK-0607
governing_adrs:
- ADR-0002
- ADR-0014
governing_prds:
- PRD-0002
governing_stories:
- US-0002
- US-0025
target_release: 0.9.0
severity: high
source_audits:
- w2-inference-worker.md
---

# TASK-0608: Inference Worker Stand-In Guardrails Contract Matches The Watcher

## Status
Complete

## Summary
The Watcher sends stand-in guardrails to the inference worker. The worker drops them, so the stand-in graph always runs with no guardrails. The worker also never reports which guardrails it applied, so The Watcher always receives an empty list. This task adds the missing fields on both sides and tests the round trip through public routes.

## Problem Statement
- `services/the_watcher/src/the_watcher/routers/stand_in.py:47` sends `"guardrails": req.guardrails`.
- `services/inference_worker/src/inference_worker/models.py:96-113` (`StandInActionRequest`) has no `guardrails` field. Pydantic drops it.
- `graphs/stand_in_graph.py:55` reads `req.get("guardrails", {})` and always gets `{}`.
- `the_watcher/routers/stand_in.py:50` reads `guardrails_applied`. `StandInActionResponse` (`models.py:116-124`) has no such field, so The Watcher always gets `[]`.

Source: `.audit/reports/w2-inference-worker.md` F1.

## Documentation & Architecture Review
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: documents guardrail names such as `protect_allies`. Confirm names and update the reply shape.
- `docs/reference/events-schema.md` if stand-in events carry guardrails.
- ADR-0002: The Watcher owns policy. The worker applies it.

## Product & User Story References
- `docs/project/product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md`
- `docs/project/user_stories/accepted/us-0025-personalized-ai-stand-in-tactical-policies.md`

## Detailed Specification & Implementation Plan
1. Add `guardrails: list[str]` (or the typed model used by The Watcher) to `StandInActionRequest`.
2. Add `guardrails_applied: list[str]` to `StandInActionResponse`.
3. In `stand_in_graph.py`, read the guardrails from the typed request. Set `guardrails_applied` from the guardrails the graph enforced. Do not echo the input list.
4. Use one shared model for the guardrail type in `libs/` if both services need it, or mirror it with a contract test.
5. The Watcher route returns `guardrails_applied` to its caller.

## Frontdoor Blackbox Test Plan
- Before fix: POST a stand-in request to The Watcher with `protect_allies`. The response `guardrails_applied` is empty (test fails).
- After fix: the response lists `protect_allies` as applied, when the graph applied it.
- After fix: a request with an unknown guardrail name returns 422 at The Watcher.
- Tests run through The Watcher public route with the worker on the mock backend (see TASK-0607).

## Definition of Done
1. Both services declare the guardrail fields. No field is silently dropped (a contract test checks it).
2. Files under 500 lines.
3. Blackbox tests pass. Pytest for both services passes.
4. Ruff check and format pass.
5. How-to updated with the response field.
