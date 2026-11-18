---
icon: lucide/sparkles
title: Platform Showcase & Vision
description: Runefoble - The AI-Native Collaborative Tabletop Roleplaying Platform. Speak and the board obeys.
---

# Runefoble: Speak and the Board Obeys

<div class="hero-banner" markdown style="padding: 1.5rem; background: linear-gradient(135deg, rgba(79, 70, 229, 0.12) 0%, rgba(147, 51, 234, 0.08) 100%); border-radius: 12px; border: 1px solid rgba(79, 70, 229, 0.25); margin-bottom: 2rem;">

### Collaborative Tabletop Roleplaying, Built on AI
**Runefoble** combines tabletop roleplaying with AI tools. The goal is to turn spoken commands into board changes in under 500 milliseconds. That speech path is not live yet. See the status tables below for each capability.

[🚀 Explore Project Visualizer](project-visualizer.md){ .md-button .md-button--primary }
[🎨 Storybook Component Studio](storybook-studio.md){ .md-button }
[📖 View Changelog](changelog.md){ .md-button }

</div>

---

## Status Legend

Every capability on this page has one status. Use these terms:

| Status | Meaning |
|---|---|
| **Live** | The code is on `main`. A frontdoor test passes. The test is named in the row. |
| **In progress** | Part of the capability works and has a passing test. The limit is stated. The blocking backlog task is named. |
| **Planned** | No working code path yet. The backlog task is named, or no task exists yet. |

A frontdoor test calls public HTTP, WebSocket, or event interfaces. Tests live in `tests/`. Paths below are relative to the repository root.

---

## 🎲 The Tabletop Dilemma & The Runefoble Goal

Every roleplaying group faces three barriers to regular game nights:

<div class="grid cards" markdown>

-   :material-clock-alert: **The DM Prep Burden**

    ---

    Game Masters spend 4 to 8 hours on maps, rule lookups, and encounter math for each session.

    **The Runefoble Goal**: **The Watcher** helps the DM with scene text, monster tactics, and rule queries. Status: **In progress**. See [The Watcher](#2-the-watcher-dm-co-pilot-and-stand-ins).

-   :material-calendar-remove: **The Missing Player Curse**

    ---

    When one player cannot attend, games are often postponed for weeks.

    **The Runefoble Goal**: AI **stand-ins** play absent characters under DM guardrails. Status: **Live** for guardrails and takeover. Session penalties are **In progress**.

-   :material-cursor-default-click: **Clunky VTT Interfaces**

    ---

    Virtual tabletops often need many menus and manual steps.

    **The Runefoble Goal**: **"Speak and the board obeys."** Status: **Planned** for the full speech path. See [Speech Path Status](#speech-path-status).

</div>

---

## ⚡ Speech Path Status

The speech path has four steps. Each step has its own status.

| Step | Status | Evidence | Blocking task |
|---|---|---|---|
| Speech to text (`/api/v1/voice/transcribe`) | **In progress** | `tests/test_blackbox_voice_transcribe_input.py`, `tests/test_blackbox_streaming_whisper_e2e.py` | TASK-0509 (no UI caller) |
| Text to intent (intent routes) | **In progress** | `tests/test_speech_to_intent.py`, `tests/test_blackbox_intent_disambiguation_flow.py` | TASK-0509 (no UI caller) |
| Gateway speak-and-act (`/api/v1/watcher/speak-and-act`) | **Live** | Proxies to The Watcher intent route, which parses the transcript (`gateway/api/src/gateway_api/routers/watcher_speech_proxy.py`, `tests/test_blackbox_gateway_speech_proxy.py`) | TASK-0583 (board apply open) |
| Board change from speech | **Planned** | The Watcher publishes `token_moved`, but `board_state` does not apply it yet | No backlog task yet |

The speech targets are not measured. The 500 millisecond target has no latency test.

---

## 🧭 Capability Status

### 1. Tactile Board

- **Live**: Board state is an event-sourced aggregate. Board changes save through `AggregateRepository` in `services/board_state`. Test: `tests/test_blackbox_board_state.py`.
- **Live**: Fog of war from token vision radius. Test: `tests/test_blackbox_board_fog_of_war.py`.
- **Live**: Spoken ghost preview route on the board service. Test: `tests/test_blackbox_ghost_previews.py`. The voice trigger is **Planned** (TASK-0509).
- **Live**: Battlemap upload to Silo S3. Test: `tests/test_blackbox_silo_asset_lifecycle.py`.
- **In progress**: Token kinematics and 5-foot waypoint measurement (TASK-0084 is complete). No passing browser test covers this behaviour in this review.
- **In progress**: Gateway board and token routes. The gateway returns fixed data for some board and token routes (`gateway/api/src/gateway_api/routers/tabletop.py`). The gateway does not yet proxy them to `board_state`. Blocking task: TASK-0582. Token authorization: TASK-0547.
- **Planned**: Light-based fog of war. No backlog task exists yet.

### 2. The Watcher: DM Co-Pilot and Stand-Ins

- **Live**: DM co-pilot whispers and veto override. A human DM can reject any AI action. Test: `tests/test_blackbox_dm_copilot_whispers.py` (TASK-0053).
- **Live**: Disambiguation and compound actions through the API. Tests: `tests/test_blackbox_intent_disambiguation_flow.py`, `tests/test_blackbox_intent_compound_combos.py` (TASK-0054).
- **Planned**: Autonomous DM mode, which runs a full session. The LLM provider path is not wired. Blocking tasks: TASK-0448, TASK-0449.
- **Planned**: Wake-word activation (US-0024). No backlog task exists yet.

### 3. Missing Player Stand-Ins

- **Live**: Stand-in guardrails, takeover when a player leaves, and hot-swap handoff. Tests: `tests/test_blackbox_leave_activates_stand_in.py`, `tests/test_blackbox_stand_in_takeover.py`, `tests/test_blackbox_standin_guardrails_persistence.py` (TASK-0055, TASK-0357, TASK-0570).
- **Live**: Absentee recap read API (chronicle feed and stand-in turns). Test: `tests/test_blackbox_session_chronicle.py` (TASK-0641).
- **In progress**: Session penalties. The Watcher writes "Drunk" and "Foolishness" text (`services/the_watcher/src/the_watcher/stand_in_guardrails.py`). Penalty records are not yet reconciled for the DM. Blocking task: TASK-0462.
- **Planned**: Catch-up recap reel for returning players. Blocking task: TASK-0463.
- **Planned**: Voice-cloned stand-in dialogue. Blocking task: TASK-0464.

### 4. Audio, Voice, and DSP

- **Live**: WebRTC voice room signaling and room persistence. Test: `tests/test_blackbox_voice_room_persistence.py` (TASK-0033).
- **Live**: Voice duplex state through the API, including speech barge-in state. Test: `tests/test_blackbox_voice_duplex.py` (TASK-0141).
- **In progress**: Voice DSP conditions. The voice agent returns DSP parameters for a status condition. Test: `tests/test_blackbox_voice_dsp_condition.py`. The browser filter chain is **Planned** (TASK-0482).
- **In progress**: Text-to-speech with an espeak-ng adapter. Test: `tests/test_blackbox_voice_tts.py` (TASK-0601). Distinct persona voice profiles are not verified.
- **In progress**: Duplex controls in the App Shell. Blocking tasks: TASK-0508, TASK-0509, TASK-0510.
- **In progress**: Adaptive soundscape mixing and tension scoring. Tests: `tests/test_blackbox_soundscape_tension.py`, `tests/test_blackbox_soundscape_ui/`. Board event cues are **Planned** (TASK-0438). The App Shell audio sync is **Planned** (TASK-0437).

### 5. Identity and Authorization

- **Live**: Zitadel OIDC token checks on HTTP and WebSocket routes. Tests: `tests/test_blackbox_zitadel_http_auth.py`, `tests/test_blackbox_zitadel_websocket_auth.py`, `tests/test_blackbox_identity_negative.py` (TASK-0034, TASK-0522, TASK-0529). The dev identity bypass was removed (TASK-0520).
- **In progress**: SpiceDB object authorization. The gateway and services check SpiceDB permissions on the routes covered by TASK-0522 to TASK-0555, TASK-0767, and TASK-0770. Tests: `tests/test_blackbox_spicedb_live.py`, `tests/test_blackbox_board_actions_authz.py`, `tests/test_blackbox_voice_authz.py`. This page does not claim that every route has a permission check.
- **In progress**: Stand-in guardrail contract. Blocking task: TASK-0691.

### 6. Microfrontends and Design System

- **Live**: Each service serves its own microfrontend manifest at `/ui/manifest`. Test: `tests/test_microfrontends.py`. Gateway-level discovery is **Planned**. No backlog task exists yet.
- **In progress**: Dark, Light, and System modes in the settings modal (TASK-0073 is complete). No frontdoor test in `tests/` covers the modal in this review.
- **In progress**: WCAG 2.1 AA contrast. `tests/test_theming_contrast.py` checks token ratios (4.5:1 body, 7:1 primary). This is a token check, not a rendered page check. Rendered contrast checks are not yet in place.

### 7. Persistence, Observability, and Analytics

- **Live**: Event sourcing on PostgreSQL for deployed services. PostgreSQL is the default event store. A deployed service refuses the memory store (`libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`). Tests: `tests/test_blackbox_postgres_event_store.py`, `tests/test_blackbox_event_store_fail_fast.py` (TASK-0036).
- **Live**: Redis Streams event fanout with consumer groups. Test: `tests/test_blackbox_stream_consumers.py` (TASK-0015).
- **Live**: Campaign chronicle timeline and telemetry API. Tests: `tests/test_blackbox_session_chronicle.py`, `tests/test_blackbox_campaign_analytics_api.py` (TASK-0052, TASK-0110).
- **In progress**: OpenTelemetry tracing. Test: `tests/test_blackbox_opentelemetry.py` (TASK-0037). Tracing is off by default (`RUNEFOBLE_OTEL_ENABLED=false`). Helm turns it on for some services only.
- **In progress**: OpenPanel analytics. Test: `tests/test_blackbox_analytics_client.py` (TASK-0038). Export to a live OpenPanel instance is not verified in this review.
- **Planned**: Time-travel debugging. No code or backlog task exists.
- **Planned**: Player achievements, badges, and recap books. Blocking tasks: TASK-0458, TASK-0459, TASK-0460.

### 8. Agent Tools (FastMCP)

- **Live**: MCP tools require a verified bearer token (TASK-0532). Tests: `tests/test_blackbox_mcp_gateway.py`, `tests/test_blackbox_mcp_upstream_calls.py`.
- **Live**: Dice rolls compute results on the server (`gateway/mcp/src/gateway_mcp/tools/dice.py`). Test: `tests/test_blackbox_mcp_orchestration_and_resources.py`.
- **Live**: Runtime dynamic tools from declarative templates (TASK-0766 removed arbitrary Python). Tests: `tests/test_blackbox_dynamic_mcp/`.
- **In progress**: Lore and compendium tools. Lore retrieval is tested with `tests/test_blackbox_campaign_lore_rag.py`. Latency is not measured.

### 9. Content and Broadcast Tools

- **Live**: Universal VTT (`.dd2vtt`) import with walls, doors, and lights. Test: `tests/test_blackbox_uvtt_import/` (TASK-0057).
- **Live**: Procedural battlemap and token generation. This is a deterministic generator, not a diffusion model. Test: `tests/test_blackbox_asset_forge_map_generator.py` (TASK-0049). Spoken prompts are not a supported input.
- **Live**: Rules compendium search and encounter builder. Test: `tests/test_blackbox_rules_compendium.py` (TASK-0048).
- **Live**: Campaign lore retrieval over ingested documents. Test: `tests/test_blackbox_campaign_lore_rag.py` (TASK-0047). Sub-50 ms retrieval is not measured.
- **Live**: Audience polls and votes through the API, with SpiceDB checks. Test: `tests/test_blackbox_audience_studio.py` (TASK-0051, TASK-0554).
- **Live**: Cinematic camera and overlay routes. Tests: `tests/test_blackbox_cinematic_director/` (TASK-0056).
- **Planned**: Twitch and YouTube chat ingestion. Blocking task: TASK-0455.
- **Planned**: OBS WebSocket bridge and Stream Deck actions. Blocking task: TASK-0456.
- **Planned**: Foundry VTT, Roll20, and Fantasy Grounds import. Only `.dd2vtt` import exists.

---

## 🗺️ Roadmap Status

Milestone status comes from [`project/backlog/ROADMAP.md`](project/backlog/ROADMAP.md). A milestone is complete when its backlog tasks are complete. A complete milestone does not mean that every capability in it is live. Use the status sections above for that.

| Milestone | Status |
|---|---|
| M1 Platform Foundation & Core Loop | Complete |
| M2 Live Collaborative Alpha | Complete |
| M3 AI DM & Ecosystem Expansion | Complete |
| M4 Broadcast Studio & Community Platform | Complete |
| M5 Collaborative Creation, Downtime & Tactile Immersion | Complete |
| M6 Intelligent Living Worlds & Spatial Multi-Party Universes | Complete |
| M7 Neural Audio Duplex & Tangible 3D Tabletop | Complete |
| M8 Reactive Tactical Environments & In-World DM Tools | Complete |
| M10 Complete Frontend Application Experience, User Identity & Campaign Orchestration | Active |

Open work in Milestone 10 includes the gateway proxies (TASK-0582, TASK-0583, TASK-0596), the audience ingestion (TASK-0455, TASK-0456), and the West Marches and absentee tasks (TASK-0451 to TASK-0465).

---

## 🔬 Architectural Transparency & Engineering Rigor

| Architectural Pillar | Specification / Implementation | Status |
|---|---|---|
| **Language & Environment** | Python 3.13 + UV Monorepo Workspace | **Live** |
| **Event Sourcing** | `eventsource-py` aggregates on PostgreSQL | **Live** (deployed services) |
| **Distributed Messaging** | Redis Streams consumer groups | **Live** |
| **Object Authorization** | SpiceDB Zanzibar (`runefoble.zed`) on covered routes | **In progress** |
| **Identity** | Zitadel OIDC on HTTP and WebSocket routes | **Live** |
| **Frontend Architecture** | Lit Web Components + Shadow DOM, per-service manifests | **Live** |
| **Design System** | Bauhaus tokens, Dark/Light/System modes, token contrast checks | **In progress** |
| **Agent Interface** | Model Context Protocol (FastMCP) gateway | **Live** (authenticated tools) |
| **Local Infrastructure** | Kind cluster, `make images`, umbrella Helm chart | **Live** (local only) |
| **Cloud Infrastructure** | Single-command cloud deployment | **Planned** (no backlog task) |

---

## 🛠️ Interactive Exploration & Documentation Hub

Explore the platform through our built-in interactive tools and documentation:

<div class="grid cards" markdown>

-   :material-graph: **[Interactive Project Visualizer](project-visualizer.md)**

    ---

    Interact with our 2D force-directed graph, DAG dependency tree, radar view, and Kanban pipeline tracking every ADR, PRD, and backlog task.

-   :material-palette: **[Storybook UI Studio](storybook-studio.md)**

    ---

    Test each Lit Web Component in isolation across themes, viewport sizes, and mock states.

-   :material-history: **[Platform Changelog](changelog.md)**

    ---

    Review each platform release, milestone deliverable, and unreleased change, following Keep a Changelog.

-   :material-school: **[Local Development Tutorial](tutorials/01-local-development-setup.md)**

    ---

    Set up a local Kind cluster and the Helm stack.

-   :material-file-document-multiple: **[Architectural Decision Records](project/adrs/REGISTRY.md)**

    ---

    Read the accepted ADRs for Zanzibar authorization, event sourcing, microfrontends, and speech processing.

-   :material-clipboard-check: **[Agent Operating Manual](operating-manual.md)**

    ---

    Read the Definition of Ready (DoR), Definition of Done (DoD), and file length rules that govern code quality.

</div>

---

## 🚀 Get Started (Local Only)

Use these steps to run the platform on a local Kind cluster:

```bash
# Clone and inspect the repository
git clone https://github.com/tyevans/runefoble.git
cd runefoble

# Create the local Kind Kubernetes cluster with Traefik ingress
make cluster-up

# Build every service image and load it into Kind
make images

# Deploy the Helm stack
make helm-deploy

# Launch the hot-reloading frontend
make dev-frontend
```

*Runefoble is in active development. The platform does not yet offer a cloud deployment.*
