---
id: '0051'
title: TypeScript Audience Studio & Live Stream Interactivity Microservice
status: Refined
created: 2026-09-25
dependencies:
- TASK-0010
- TASK-0014
- TASK-0016
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0007
- ADR-0013
target_release: 0.3.0
---

# TASK-0051: TypeScript Audience Studio & Live Stream Interactivity Microservice

## Status
Refined

## Summary
Scaffold `services/audience_studio` as a first-class **TypeScript backend microservice** (Node.js / Fastify / TypeScript) leveraging the streaming ecosystem (`obs-websocket-js`, Twitch chat/polls, Stream Deck SDKs) and subscribing to Redis Streams to deliver live spectator interactivity without adding latency to core gameplay.

## Problem Statement
Live tabletop streaming sessions require high-concurrency event ingestion from Twitch chat votes, YouTube Live polls, OBS studio WebSockets, and hardware macro decks (Elgato Stream Deck). Managing bidirectional audience engagement in Python creates ecosystem friction with streaming tools and risks table gameplay latency.

A dedicated TypeScript bounded context microservice (`services/audience_studio`) acts as a shock absorber:
1. Ingests high-frequency spectator chat votes and channel point redemptions.
2. Aggregates chaos polls into summarized modifier proposals.
3. Coordinates with The Watcher and the DM co-pilot via Redis Streams (`AudiencePollCompleted`, `AudienceModifierProposed`).
4. Exposes a live DM approval queue WebSocket and frontdoor REST API.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforces `spectator` relation and `dungeon_master` moderation approvals.
- **ADR-0003: UV Monorepo Workspace for Python Bounded Contexts**: Preserves monorepo boundaries while supporting TypeScript services.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Umbrella Helm deployment for `audience_studio`.
- **ADR-0006: Redis Streams Transport Architecture**: Subscribes to session events and publishes audience CloudEvents.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Sub-500ms broadcast synchronization.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Exposes `<runefoble-audience-studio>` microfrontend.

## Scope of Work
1. **TypeScript Service Scaffolding (`services/audience_studio/`)**:
   - Fastify HTTP and WebSocket server with OpenAPI `/openapi.json` documentation.
   - Redis Streams consumer and publisher using `ioredis` with CloudEvents 1.0 JSON payloads.
2. **Audience Poll Engine**:
   - Ingestion endpoints for live polls (`POST /api/v1/audience/polls`).
   - Real-time vote aggregation with time window expiration and quorum calculation.
3. **DM Approval Queue & WebSocket**:
   - WebSocket channel (`/ws/audience/{campaign_id}`) for live DM veto/approval of audience modifiers.
   - SpiceDB Zanzibar check: only `dungeon_master` can approve chaos modifiers.
4. **CloudEvents Definitions**:
   - Emits `AudiencePollStarted`, `AudienceVoteCast`, `AudiencePollCompleted`, and `AudienceModifierApproved`.
5. **Helm & Gateway Integration**:
   - Service deployment manifest and Traefik ingress route in `deployments/helm/runefoble/templates/audience-studio.yaml`.
   - OpenAPI spec aggregation in Swagger UI hub.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates as an independent microservice over Redis Streams without direct coupling to Python service internals.
- **Negotiable (N)**: Specific voting algorithms and external platform adapters can evolve incrementally.
- **Valuable (V)**: Delivers core streaming capabilities for content creators and audience participation without table lag.
- **Estimable (E)**: Standard Fastify service scaffolding following repo patterns.
- **Small (S)**: Scope strictly focused on audience poll lifecycle and Redis event streaming; all source files < 250 lines.
- **Testable (T)**: Full frontdoor blackbox test suite with HTTP and WebSocket test clients.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Frontdoor Blackbox Verification**:
   - End-to-end blackbox test suite in `tests/test_blackbox_audience_studio.py` testing poll creation, spectator voting, quorum aggregation, and DM approval.
   - Interacts strictly via public Fastify REST routes and Redis Streams event bus.
2. **CloudEvents Compliance**:
   - Domain events registered and serialized according to CloudEvents 1.0 specification.
3. **OpenAPI Hub Exposure (Hard Invariant 5)**:
   - Exposes `/openapi.json` and registered in Swagger UI values.
4. **File Length Limits (Hard Invariant 6)**:
   - Zero files exceeding 250 lines.
5. **Helm & Kubernetes Deployability (Hard Invariant DoD 7)**:
   - Helm chart renders cleanly (`helm template`) and passes `helm lint`.
