# Changelog

All notable changes to the Runefoble platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

- **Bespoke Antigravity (AGY) Agent Launcher for Project Visualizer (`tools/project_visualizer/`)**:
  - Direct execution of `agy --dangerously-skip-permissions -p <prompt>` via non-blocking background thread manager (`AgyRunnerManager`).
  - Interactive AGY Launcher modal with live-streaming console logs, process termination controls, and routine presets (`Task Spec`, `Curator`, `Health & Invariants`, `TDD Verification`).
  - Context-aware "Launch AGY" task dispatch in detail drawers pre-filling bespoke prompts with task metadata, specification paths, and the Runefoble Definition of Done.
  - Strict GitHub Pages build isolation: interactive agent runner controls and scripts are gated strictly to local live servers (`is_live_server=True`), ensuring zero leakage into static documentation bundles (`site/`, `dist/`).
- **Platform Showcase & Marketing Page (`docs/marketing.md`)**: Comprehensive public product showcase and vision document in GitHub Pages docs highlighting "Speak and the board obeys", tactical board kinematics, sub-500ms voice pipeline, The Watcher AI DM, and the multi-horizon roadmap (`ROADMAP.md`).
- **Changelog Tracking (`CHANGELOG.md`)**: Established standard Keep a Changelog repository ledger integrated into GitHub Pages static build synchronization (`docs/changelog.md`).
- **Definition of Done Integration**: Formalized Changelog Maintenance as an invariant requirement in the repository Definition of Done (`AGENTS.md`, `docs/project/backlog/README.md`, `docs/how-to/curate-backlog-and-roadmap.md`).
- **Blackbox Documentation & Pages Test Suite**: Expanded `tests/test_docs_build_and_pages.py` to assert changelog existence, Keep a Changelog structure, Definition of Done enforcement, and marketing page navigation integrity.

### Changed
- **Documentation Navigation**: Featured the Platform Showcase and Changelog in `zensical.toml` and the root documentation landing page (`docs/index.md`).
- **Build Automation**: Enhanced `scripts/build_docs.py` to synchronize `CHANGELOG.md` to `docs/changelog.md` during documentation compilation.

---

## [0.2.0] - 2026-09-26

### Milestone 2: Live Collaborative Alpha

#### Added
- **Tactile Board Kinematics & Ghost Previews (`TASK-0084`, `PRD-0013`, `US-0043`)**:
  - Drag-and-drop token physics with spring damping, velocity, 5ft step counting, and live waypoint route measurement.
  - Semi-transparent ghost preview trajectories for spoken movement commands before state commits.
  - Movement path validation against difficult terrain, hazards, and spatial boundary walls.
- **Streaming Whisper Speech-to-Intent Pipeline (`TASK-0039`, `TASK-0083`)**:
  - Sub-500ms streaming Whisper audio transcription and intent classification.
  - Real-time voice intent extraction for movement, attacks, spells, and narrative statements.
  - Multi-condition DSP voice filters for drunkenness slurs, ghost echoes, and underwater muffling.
- **Microfrontend Component Architecture (`ADR-0013`, `TASK-0024`, `TASK-0043`)**:
  - Service bounded context component vendoring in `services/<bc>/ui/` with Shadow DOM encapsulation.
  - Runtime dynamic microfrontend discovery via `/ui/manifest` endpoints.
  - Decoupled Lit Web Component App Shell (`frontend/`) and Storybook component studio integration.
- **Frontend Settings Modal & Theme Modes (`TASK-0073`, `TASK-0086`)**:
  - Centralized settings modal with Dark, Light, and System preference mode orchestration.
  - High-contrast Bauhaus modernist design tokens ensuring WCAG 2.1 AA compliance.
- **Live WebRTC Audio & S3 Asset Uploaders (`TASK-0030`, `TASK-0031`, `TASK-0033`)**:
  - WebRTC bidirectional voice room with real-time audio waveform visualizer microfrontend.
  - Silo S3 battlemap uploader with dynamic shroud masking and asset persistence.
- **Enterprise Security & Event Store (`TASK-0032`, `TASK-0034`, `TASK-0035`, `TASK-0036`)**:
  - Google Zanzibar fine-grained object-level authorization powered by SpiceDB (`runefoble.zed`).
  - Zitadel OIDC identity authentication with JWT/JWKS verification middleware.
  - PostgreSQL multi-database persistent event store powered by `eventsource-py` declarative aggregates.
  - High-throughput Redis Streams event bus across distributed microservice nodes (`TASK-0015`, `TASK-0042`).
- **Observability & Analytics (`TASK-0037`, `TASK-0038`, `TASK-0082`)**:
  - OpenTelemetry distributed tracing and metrics with Collector, Loki, and Grafana integration.
  - Privacy-preserving OpenPanel analytics SDK and Redis Streams event worker.
- **Autonomous Backlog Execution Engine (`TASK-0046`)**:
  - Parallel worktree orchestrator (`scripts/run-backlog-engine.sh`) with conflict detection, CI healing, and non-blocking merge locks.
  - Interactive Project Visualizer web application and standalone HTML graph generator.

#### Changed
- **Modular Router Refactoring (`TASK-0040`, `TASK-0041`, `TASK-0045`, `TASK-0085`)**:
  - Decomposed monolithic FastAPI entrypoints into modular sub-routers across all bounded contexts.
  - Decomposed FastMCP tabletop gateway tools and resources into modular registries.

---

## [0.1.0] - 2026-09-20

### Milestone 1: Platform Foundation & Core Loop

#### Added
- **Monorepo Workspace Foundation (`TASK-0000`, `ADR-0003`)**:
  - UV workspace monorepo managing shared libraries and services.
  - Shared packages: `runefoble_platform`, `runefoble_auth`, `runefoble_events`.
- **Core Microservices**:
  - `the_watcher`: Autonomous DM, speech-to-intent engine, and absentee player stand-in.
  - `game_session`: Session lifecycles, initiative order, turns, and dice roll mechanics.
  - `board_state`: Tactical square/hex grid, token positioning, and fog of war.
  - `character_sheet`: Character stats, HP tracking, inventory, and session miss penalties.
  - `voice_agent`: WebRTC voice streaming, STT/TTS pipeline, and audio DSP.
- **Unified API Gateway & FastMCP**:
  - API Gateway aggregating HTTP, WebSockets, and OpenAPI specs into Swagger UI.
  - FastMCP gateway exposing tabletop tools and game resources to LLM agents.
- **Infrastructure & Frontend**:
  - Local Kubernetes Kind cluster setup with Traefik ingress and umbrella Helm chart.
  - Lit + Vite frontend with Storybook design system aggregator and Bauhaus tokens.
- **Diataxis Documentation System**:
  - Complete Diataxis documentation suite (tutorials, how-to guides, reference, explanations).
