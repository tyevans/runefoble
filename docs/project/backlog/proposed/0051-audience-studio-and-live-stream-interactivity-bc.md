---
id: 0051
title: TypeScript Audience Studio & Live Stream Interactivity Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0010, TASK-0014, TASK-0016]
governing_adrs: [ADR-0001, ADR-0007]
target_release: 0.3.0
---

# TASK-0051: TypeScript Audience Studio & Live Stream Interactivity Microservice

## Status
Proposed

## Summary
Scaffold `services/audience_studio` as a first-class **TypeScript backend microservice** (Node.js / Fastify / TypeScript) leveraging the rich TypeScript streaming ecosystem (`obs-websocket-js`, Twitch EventSub/IRC, Stream Deck SDKs) and subscribing to Redis Streams.

## Problem Statement
Live tabletop streams (Devon) require high-concurrency event ingestion from Twitch chat, YouTube Live, OBS studio WebSockets, and hardware macro decks. Managing bidirectional audience engagement in Python creates ecosystem friction with streaming tools and risks table gameplay latency.

## Scope of Work
1. **TypeScript Backend Scaffolding**: Create `services/audience_studio` using Node.js, Fastify, TypeScript, and pnpm workspace tooling alongside Docker/Helm deployment manifests.
2. **Redis Streams Consumer**: Connect to Redis Streams (`ioredis`) to publish and subscribe to Runefoble CloudEvents.
3. **Audience Chaos Polls**: Implement high-throughput polling engine consuming Twitch Channel Points and YouTube Live chat votes.
4. **OBS WebSocket & Stream Deck Integration**: Provide native TypeScript connectors (`obs-websocket-js`, `@elgato/streamdeck`) for automated scene switching and director camera cues.
5. **DM Approval Queue**: Provide a real-time WebSocket queue for DMs to approve audience-voted modifiers before execution.

## Acceptance Criteria
1. TypeScript backend handles 2,000+ concurrent spectator WebSocket connections and chat votes under 20ms latency.
2. Bidirectional event publishing/consumption over Redis Streams interoperates cleanly with Python services.
3. Automated OBS scene switching and Stream Deck hotkeys trigger successfully in end-to-end integration tests.
