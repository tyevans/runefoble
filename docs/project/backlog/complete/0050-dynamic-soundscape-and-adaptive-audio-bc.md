---
id: '0050'
title: Dynamic Soundscape & Adaptive Audio Microservice
status: Complete
created: 2026-09-25
dependencies:
- TASK-0006
- TASK-0021
- TASK-0025
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0007
- ADR-0010
- ADR-0011
- ADR-0013
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/70
---
# TASK-0050: Dynamic Soundscape & Adaptive Audio Microservice

## Status
Refined

## Summary
Scaffold a new bounded context `services/soundscape` responsible for dynamic background audio stem mixing, tactical foley sound effects, and tension-based music progression synchronized with game session events and voice activity.

## Problem Statement
Tabletop audio immersion currently suffers because `voice_agent` only handles spoken dialogue. DMs must manually DJ background music and foley, which creates friction and breaks storytelling immersion (PRD-0010, US-0039). The platform requires an autonomous audio service that dynamically scores encounter tension (0–100), crossfades atmospheric music stems, and automatically ducks background audio during player voice transmission.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts (`services/soundscape`).
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (`deployments/helm/runefoble/templates/soundscape.yaml`).
- **ADR-0006**: Redis Streams Event Bus Transport (`CombatStarted`, `CombatRoundAdvanced`, `SoundscapeTrackChanged`).
- **ADR-0007**: Real-Time Voice and Board Synchronization (sub-500ms pipeline and WebAudio ducking).
- **ADR-0010**: OpenTelemetry Distributed Tracing & Metrics instrumentation.
- **ADR-0011**: eventsource-py Core Event Sourcing (`SoundscapeAggregate`).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`/ui/manifest` and `<runefoble-soundscape-controls>`).

## Product & User Story References
- **Product Requirement**: [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- **User Story**: [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)

## Scope of Work
1. **Bounded Context Package Scaffolding (`services/soundscape`)**:
   - Initialize `services/soundscape` registered in root `pyproject.toml`.
   - Setup FastAPI application exposing `/healthz`, `/openapi.json`, and `/ui/manifest`.
2. **Encounter Tension Scoring Engine**:
   - Compute real-time tension metric (0–100) derived from combat round progression, active enemy CR balance, and lowest party health ratios.
3. **Adaptive Audio Stem Mixer & WebAudio Ducking**:
   - Expose stem tracks (ambient, tension, combat, boss) with smooth transition interpolation.
   - Ducking coordinator muting/attenuating music layers by -12dB when active speech events or WebRTC voice frames arrive.
4. **Microfrontend Controls (`services/soundscape/ui/`)**:
   - Implement `<runefoble-soundscape-controls>` Lit Web Component for master volume, stem toggles, and manual DM mood overrides.
   - Vendor bundle and manifest at `GET /ui/manifest`.
5. **Frontdoor Blackbox Verification**:
   - Comprehensive test suite in `tests/test_blackbox_soundscape.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates as an autonomous microservice communicating via standard HTTP REST endpoints and Redis Streams domain events.
- **Negotiable (N)**: Audio stem format (OGG/MP3/WAV) and ducking curve parameters can be configured.
- **Valuable (V)**: Automates ambient immersion for DMs and players (core Milestone 3 value in PRD-0010).
- **Estimable (E)**: Follows the established microservice pattern of `campaign_lore` (TASK-0047) and `asset_forge` (TASK-0049).
- **Small (S)**: Scope modularly partitioned across routers, audio mixer, domain aggregate, and microfrontend; all files < 300 lines.
- **Testable (T)**: Verifiable via public HTTP API routes (`POST /api/v1/soundscape/cue`, `GET /api/v1/soundscape/tension`) and CloudEvents.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Bounded Context Scaffolding**:
   - `services/soundscape` added to root `pyproject.toml` workspace and passing `uv run pytest`.
2. **Public HTTP Frontdoor API**:
   - `POST /api/v1/soundscape/cue`: Triggers tactical sound foley or mood cue.
   - `GET /api/v1/soundscape/tension`: Returns current session tension index and active stem profiles.
   - `GET /healthz` and `GET /ui/manifest` exposed.
3. **Domain Event Publication & Subscription**:
   - Emits CloudEvent `SoundscapeTrackChanged` over Redis Streams.
   - Subscribes to `CombatStarted` and `CombatRoundAdvanced` to update tension scores automatically.
4. **Microfrontend & Storybook**:
   - `<runefoble-soundscape-controls>` built with Shadow DOM and Bauhaus design tokens.
   - Storybook stories added with zero console errors.
5. **Helm Integration**:
   - Deployment, Service, and ConfigMap added to umbrella Helm chart.
6. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_soundscape.py` verifying public routes, event bus subscriptions, and manifest discovery.
7. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run ruff check` and `uv run ruff format --check`.
