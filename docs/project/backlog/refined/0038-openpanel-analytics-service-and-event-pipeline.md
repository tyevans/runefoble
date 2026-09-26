---
id: '0038'
title: OpenPanel Privacy-Preserving Analytics SDK & Event Pipeline
status: Refined
created: 2026-09-25
dependencies: [TASK-0001, TASK-0015]
governing_adrs: [ADR-0005, ADR-0006, ADR-0007]
target_release: 0.1.0
---

# TASK-0038: OpenPanel Privacy-Preserving Analytics SDK & Event Pipeline

## Status
Refined

## Summary
Implement a privacy-preserving analytics client (`OpenPanelClient`) in `libs/runefoble_platform/analytics.py` integrating with self-hosted OpenPanel (`http://openpanel:3000`). Deploy an asynchronous analytics event worker consuming key domain events from Redis Streams (e.g. `GameSessionStarted`, `DiceRolled`, `StandInTurnExecuted`, `PlayerAbsenteePenalized`) to measure gameplay engagement, session duration, and feature adoption without logging personally identifiable audio or speech content.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing CloudEvents from Redis Streams asynchronously; does not introduce runtime dependencies or block synchronous game loops.
- **Negotiable (N)**: Anonymization salt, tracked event taxonomy, and batching intervals are configurable.
- **Valuable (V)**: Provides privacy-preserving insights into game session frequency, stand-in AI usage, and platform reliability without compromising player privacy.
- **Estimable (E)**: Standard HTTP JSON analytics tracking API (`/api/event`), modeled against OpenPanel documentation.
- **Small (S)**: Scope is limited to `libs/runefoble_platform/src/runefoble_platform/analytics.py`, a background consumer worker, and tests.
- **Testable (T)**: Frontdoor blackbox tests dispatching domain events through public endpoints and asserting the analytics worker records corresponding anonymized events to an HTTP mock OpenPanel receiver.

## Governing Architecture & ADRs
- **ADR-0005**: Kubernetes-First Infrastructure with OpenPanel self-hosted analytics.
- **ADR-0006**: Redis Streams Event Streaming.
- **ADR-0007**: Domain-Driven Design Architecture (analytics decoupled from core domain aggregates).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Analytics Client (`libs/runefoble_platform/src/runefoble_platform/analytics.py`)**:
   - `OpenPanelClient` with `track(event_name: str, properties: dict, profile_id: str | None = None)` supporting async non-blocking dispatch and in-memory mock recording.
2. **Domain Event Stream Consumer**:
   - Background consumer group worker mapping published CloudEvents to anonymized OpenPanel metrics (`session.started`, `dice.rolled`, `stand_in.turn_taken`).
3. **Ingress Route (`deployments/helm/runefoble/templates/ingress.yaml`)**:
   - Expose `/analytics` path to `openpanel:3000` for client-side frontend tracking.
4. **Blackbox TDD Suite (`tests/test_blackbox_openpanel_analytics.py`)**:
   - Tests exercising game actions (e.g. session start, dice roll), verifying expected analytics payloads are constructed and sent.
5. **Diataxis Documentation**:
   - Create `docs/how-to/track-analytics-events.md`.
6. **File Invariant Check**:
   - All modified files remain strictly under 500 lines.
