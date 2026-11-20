---
id: '0969'
title: Stand-In Guardrails Are Enforced on the Model Decision, Not Only Written in the Prompt
status: Proposed
created: 2026-11-19
dependencies:
- '0943'
governing_adrs:
- ADR-0022
- ADR-0015
governing_prds:
- PRD-0002
- PRD-0025
governing_stories:
- us-0017-human-dm-veto-and-narrative-copilot-whispers
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0969: Stand-In Guardrails Are Enforced on the Model Decision, Not Only Written in the Prompt

## Status

Proposed

## Summary

TASK-0943 removed the local rule-based stand-in engine (ADR-0022 (d)). Now the inference worker is the only stand-in engine. `services/inference_worker/src/inference_worker/graphs/stand_in_graph.py` writes each active guardrail (preserve spell slots, protect allies, avoid melee, custom priorities) into the prompt as a note, and keeps only the guardrail names that the model says it followed. Nothing checks the decision against the guardrails, so the model can choose a melee attack when `avoid_melee` is on. No worker-backed test covers the guardrail rules (`.audit/work/0943.md`, item 2).

## Scope

1. After the model returns a decision, a deterministic check compares the action with each active guardrail. A decision that breaks a guardrail is not sent to the board. The Watcher returns it to the DM as a refused stand-in action with the guardrail name (the DM keeps authority, AGENTS.md design principles). It never replaces the action with a made-up one (ADR-0015).
2. Worker-backed blackbox tests with the live loopback fake OpenAI-compatible server: a decision that follows the guardrails passes; a melee decision with `avoid_melee` is refused and names the guardrail; a decision that spends a reserved spell slot is refused.
3. Docs: `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` states that guardrails are checked on every decision.
