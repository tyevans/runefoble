---
id: '0691'
title: Stand-In Guardrail Contract Is Typed and Enforced in Every Engine
status: Refined
created: 2026-11-17
dependencies:
- TASK-0690
- TASK-0608
- TASK-0609
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0002
governing_stories:
- US-0025
target_release: 0.9.0
---

# TASK-0691: Stand-In Guardrail Contract Is Typed and Enforced in Every Engine

## Status
Refined. Discovered in round 2 audit of report 0608. Follow-on to TASK-0608 and TASK-0609.

## Summary
The guardrail policy has three gaps. Autopilot forwards an untyped dict to The Watcher. The local engine reports descriptive sentences in `guardrails_applied` while the worker reports policy names. The worker reads `preserve_spell_slots` and `custom_priorities` only as prompt text, so mock output ignores them. This task defines one typed policy and makes each engine apply and report it the same way.

## Problem Statement
- `services/game_session/src/game_session/routers/autopilot.py:85` and `:105`: `request_data.guardrails` is an untyped dict. Unknown keys return 422 at The Watcher, and game_session then falls back to its local engine with no log entry.
- `services/the_watcher/src/the_watcher/stand_in_guardrails.py:35`: the local engine reports `"Prioritized protection for {ally}"`, not a guardrail name.
- `services/inference_worker/src/inference_worker/graphs/stand_in_graph.py:64-66`: `preserve_spell_slots` appears only in prompt notes. No mock-mode rule enforces it.
- `services/the_watcher/src/the_watcher/stand_in_guardrails.py` reads `custom_priorities` and `preserve_spell_slots` but does not enforce them either.

## Documentation & Architecture Review
- PRD-0002 and US-0025: guardrails are personal tactical policies. The contract must match the stored policy.
- ADR-0015 (b): no canned guardrail output. A failed engine call is an error, not a default.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` and `docs/reference/inference-worker-response-contract.md`: update the field list.

## Product & User Story References
- PRD-0002 and US-0025 (personalized stand-in guardrails).

## Detailed Specification & Implementation Plan
1. Define one typed `StandInGuardrailPolicy` model in `libs/runefoble_events` or the shared contract module. Use it in autopilot, The Watcher and the inference worker.
2. Autopilot validates the stored policy against the model before forwarding. A policy that fails validation is an error response, not a silent fallback.
3. The local engine and the worker report guardrail names from one enumeration.
4. Mock mode applies `preserve_spell_slots` and `custom_priorities` in the decision rules (for example, reserve a slot count and order the priorities). Test each rule.
5. Remove the untyped pass-through.

## Frontdoor Blackbox Test Plan
- Set a policy with `preserve_spell_slots` through the public guardrail route. Trigger an autopilot action through the public session route. Assert the action keeps the reserved slots.
- Assert `guardrails_applied` contains only names from the enumeration, for both engines (run with and without the worker).
- Send an invalid policy. Assert a 422 with the field name, and no fallback action.

## Definition of Done
- One typed model in use. No untyped guardrail dict remains in the path.
- Both engines report the same names. The two spell and priority rules are enforced in mock mode.
- `uv run pytest` and `make lint` pass. Docs updated.

## Audit Provenance

- Severity: medium
- Source audits: `work/0608.md`
