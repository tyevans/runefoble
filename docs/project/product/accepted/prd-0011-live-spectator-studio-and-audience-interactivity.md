---
id: 0011
title: Live Spectator Studio & Two-Way Audience Interactivity
status: Accepted
created: 2026-09-25
---

# PRD-0011 — Live Spectator Studio & Two-Way Audience Interactivity

## Who this is for

Content creators (Devon) streaming tabletop roleplaying sessions on Twitch/YouTube and thousands of live audience spectators.

## What the person cannot do today

Currently, virtual tabletop stream setups rely on screen capture with cluttered UI elements, manual scene switching, and zero direct audience participation in game mechanics.

## What good looks like

- **High-Concurrency TypeScript Backend**: Implemented as a dedicated TypeScript backend microservice (`services/audience_studio` in Node.js/Fastify) leveraging the native TypeScript streaming ecosystem: Twitch IRC/EventSub, YouTube Live Chat APIs, `obs-websocket-js`, and Stream Deck SDKs.
- **Broadcast Studio Overlay Mode**: Transparent, clean, responsive UI layer showing party health bars, active afflictions, and dynamic dice roll animations designed for OBS/Streamlabs browser sources.
- **Cinematic Director Auto-Camera**: Autonomous virtual camera tracking the active character token, zooming into critical encounters and panning smoothly without manual DM interaction.
- **Audience Chaos Polls & Channel Point Interactivity**: Viewers can vote or spend channel points on minor environmental effects (e.g. weather changes, minor potion drops, tavern brawls) vetted by The Watcher.

## What this does not do

- It does not permit spectators to break game balance; audience actions are strictly governed by DM approval thresholds.
- It does not leak secret DM notes, hidden traps, or private monster HP values to the broadcast feed.

## What it costs at scale

High-concurrency read-only WebSocket connections; handled via edge Redis fanout and CDN caching.

## Checkable Outcomes

1. TypeScript backend service handles thousands of concurrent Twitch/YouTube chat events and OBS WebSocket commands.
2. OBS browser source renders a transparent party HUD that updates with zero latency over WebSockets.
3. Spectator poll results trigger structured in-game events delivered via Redis Streams.

## Linked User Stories
- [`US-0006: Real-Time Spectator Stream and Chronicle`](../../user_stories/accepted/us-0006-realtime-spectator-stream-and-chronicle.md)
- [`US-0029: Spectator Dynamic Cinematic Auto-Camera and Safe View Redaction`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
- [`US-0030: OBS Transparent Party Vitals Overlay and Multi-Track Audio Output`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)
- [`US-0031: Live Stream Audience Chaos Polls via TypeScript Backend`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Implementing Backlog Tasks
- [`TASK-0051: TypeScript Audience Studio & Live Stream Interactivity Microservice`](../../backlog/complete/0051-audience-studio-and-live-stream-interactivity-bc.md)
- [`TASK-0056: Cinematic Director Auto-Camera and OBS Stream Overlay`](../../backlog/complete/0056-cinematic-director-auto-camera-and-obs-overlay.md)
- [`TASK-0075: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition`](../../backlog/complete/0075-spectator-view-stream-overlay-test-suite-decomposition.md)
- [`TASK-0439: Gateway Audience Studio API Routing & Zanzibar Authorization Proxy`](../../backlog/proposed/0439-gateway-audience-studio-api-routing-and-zanzibar-proxy.md)
- [`TASK-0440: App Shell Audience Studio Chaos Poll Drawer & Live Voting Integration`](../../backlog/proposed/0440-app-shell-audience-studio-chaos-poll-drawer-and-voting-integration.md)
- [`TASK-0441: Audience Chaos Modifiers Event Bridge & Game Session Mutation Handlers`](../../backlog/proposed/0441-audience-chaos-modifiers-event-bridge-and-game-session-mutations.md)
- [`TASK-0455: Audience Studio Twitch EventSub and YouTube Live Chat Ingestion Engine`](../../backlog/proposed/0455-audience-studio-twitch-eventsub-and-youtube-chat-ingestion.md)
- [`TASK-0456: Audience Studio OBS WebSocket Bridge and Stream Deck Hardware Actions`](../../backlog/proposed/0456-audience-studio-obs-websocket-bridge-and-stream-deck-actions.md)
- [`TASK-0457: Spectator Overlay Multi-Track Audio Routing and Stem Isolation`](../../backlog/proposed/0457-spectator-overlay-multi-track-audio-routing-and-stem-isolation.md)
