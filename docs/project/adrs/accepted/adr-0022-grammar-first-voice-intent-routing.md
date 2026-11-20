# ADR-0022: Grammar-First Intent Routing for the Voice Loop

## Status
Accepted (2026-11-19). The user chose grammar-first routing for release one.

## Context
The first release is voice first: a player holds Push to Talk, speaks, sees a ghost preview on the board, and confirms it (PRD-0025). The design principle "Speak and the board obeys" sets a 500 ms target from speech to board change (AGENTS.md, Design Principles).

The research for the release (`.audit/research/r1-watcher-llm.md`, `.audit/research/r1-voice-path.md`) found:

1. **One switch selects every engine.** `RUNEFOBLE_WATCHER_ENGINE` selects the intent parser, the stand-in engine and the narration engine together (`services/the_watcher/src/the_watcher/engine_selection.py:29-38`). Helm sets `inference_worker` (`deployments/helm/runefoble/values.yaml:316`). Every transcript therefore goes to the LLM worker, with a 2 s budget (`adapters/worker_engines.py:44`). A 27B-class model on a consumer GPU is not measured, and is not likely to meet 500 ms.
2. **The grammar is deterministic and fast.** The rule parser (`movement_parser.py:59-173`) handles coordinate moves, cardinal moves, attacks, skill checks and dice. Its test asserts a maximum under 200 ms and an average under 10 ms (`tests/test_speech_to_intent.py:146-172`). It does not yet resolve token names to cells, and it does not accept a possessive such as "move my warrior to the chest" (`grammars.py:44`).
3. **The compound route already uses only the grammar** (`routers/intent/compound.py:59`). This is not stated in any decision.
4. **ADR-0015 forbids fallbacks that hide a failure** (Context item 4). If the LLM fails, the platform must not send the transcript to the grammar instead. A routing policy that is fixed before the call is not a fallback.

Options considered:

- **Option A. LLM for every transcript (today).** One model for all speech. The voice loop then depends on the GPU host and on model latency for each spoken move.
- **Option B. Grammar for every transcript.** Fast, but no free-form speech, and no narration or stand-ins from the model.
- **Option C. Grammar first, by intent class.** The grammar parses each transcript. A transcript that the grammar parses to a board action (move, attack, skill check, dice) is applied through the normal preview and confirm path. A transcript that the grammar does not parse goes to the LLM worker, when the worker is configured. Narration and stand-ins use their own engines, which are selected one by one.

## Decision
Use **Option C**.

### (a) The grammar parses every transcript first
The Watcher sends each transcript to the grammar parser. A result of class move, attack, skill check or dice goes on to the board preview path. The grammar result records `source: "watcher_rules"`.

### (b) The LLM receives only what the grammar does not parse
A transcript that the grammar returns as `narrative` (not understood as a board action) goes to the LLM intent engine, if one is configured. The result records `source: "llm"`. When no LLM intent engine is configured, The Watcher returns "not understood" to the player. It never invents an action.

### (c) A failure is never sent to another engine
This is a routing rule, not a fallback. If the LLM call fails or times out, The Watcher returns 503 (ADR-0015). It does not try the grammar again or use a different engine. If the grammar raises an error, The Watcher returns the error. It does not send the transcript to the LLM.

### (d) Each engine port has its own setting
The single `RUNEFOBLE_WATCHER_ENGINE` switch is replaced by one setting for each port: the intent fallthrough engine, the stand-in engine and the narration engine. Each setting accepts `inference_worker` or `none`. `none` means the port is not configured, and its routes return 503 or "not understood" as stated above. Old setting names are removed, with no alias (DoR 9).

### (e) Latency is measured before a target is claimed
The release measures the time from Push to Talk release to the ghost banner on Kind with the real speech-to-text engine. The platform states a latency target only after that measurement.

## Consequences

- **Positive**:
  - A spoken board action does not depend on the GPU host or on model latency.
  - The compound route and the speech route follow the same stated rule.
  - The narration and stand-in engines can use the LLM while the voice loop stays deterministic.
- **Negative**:
  - The grammar must grow for the release phrases (possessives, token names, "my <class>").
  - Two code paths produce intents. The result field `source` must stay accurate.
  - Free-form speech that the grammar mis-parses as a board action does not reach the LLM. The player still confirms every move, so a mis-parse never changes the board without consent.
- **Follow-up**: The PRD-0025 release tasks implement (a) to (e). TASK-0448 and TASK-0449 are re-scoped against this decision.

## References

- ADR-0015: Audit Remediation Decisions (no hidden fallbacks).
- ADR-0002: Event-Driven Gameplay Architecture and The Watcher AI Engine.
- `docs/how-to/add-an-engine-port-adapter.md`.
- PRD-0025: Voice-First First Release.
