# Changelog

All notable changes to the Runefoble platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- **WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition (`TASK-0064`, `ADR-0001`, `ADR-0002`, `ADR-0003`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed monolithic `gateway/api/src/gateway_api/webrtc_signaling.py` (382 lines) into focused submodules in `gateway_api/signaling/`:
    - `gateway_api/signaling/manager.py` (119 lines): `WebRTCSignalingManager` managing active room WebSockets, peer lookups, disconnects, and broadcasts.
    - `gateway_api/signaling/auth.py` (66 lines): Credential extraction from query params/headers (`extract_signaling_auth`) and SpiceDB Zanzibar permission checks (`validate_voice_connection`).
    - `gateway_api/signaling/handlers.py` (206 lines): Dispatchers for SDP offer/answer, trickle ICE candidates, mute toggles, telemetry, and room departures.
    - `gateway_api/signaling/endpoint.py` (116 lines): WebSocket connection lifecycle endpoint `voice_signaling_websocket_endpoint`.
    - `gateway_api/signaling/__init__.py` (41 lines): Re-exports all core signaling symbols.
    - `gateway_api/webrtc_signaling.py` (28 lines): Backward-compatible facade re-exporting all primary interfaces with zero breaking changes.
  - Decomposed monolithic test suite `tests/test_blackbox_webrtc_signaling.py` (350 lines) into two focused, single-responsibility suites:
    - `tests/test_blackbox_webrtc_auth.py` (171 lines): Zanzibar permission rejection, authorized connection handshakes, header/bearer credential variants, and lifecycle CloudEvents.
    - `tests/test_blackbox_webrtc_routing.py` (218 lines): Multi-peer SDP offer/answer relay, trickle ICE routing, mute broadcasts, telemetry reporting, and DM kick moderation.
  - Enforced Hard Invariant 6 (< 500 lines limit, all modified/new files < 250 lines).

  - Decomposed monolithic `tools/backlog_engine/orchestrator.py` and `tools/backlog_engine/ci_watcher.py` into specialized, single-responsibility submodules strictly adhering to Hard Invariant 6 (< 500 lines per file, all files < 250 lines).
  - Created `tools/backlog_engine/github_client.py` (152 lines) extracting subprocess wrappers for GitHub CLI (`gh pr view`, `gh pr checks`, `gh pr create`, `gh pr close`, `gh pr merge`, and failed log retrieval).
  - Created `tools/backlog_engine/git_ops.py` (190 lines) isolating branch checkout, worktree synchronization, pre-push `git merge-tree` conflict checks, conflict resolution prompt dispatching, and atomic merge execution.
  - Streamlined `tools/backlog_engine/ci_watcher.py` (220 lines) to focus on mechanical check polling loops, failure classification, and automated PR repair dispatching.
  - Streamlined `tools/backlog_engine/orchestrator.py` (225 lines) to focus on task queue monitoring, worker pool concurrency management, and autonomous drain loops.
  - Added frontdoor blackbox test suites `tests/test_backlog_orchestrator.py` and `tests/test_pr_conflict_detection.py` verifying end-to-end automation flow.
  - Updated Diataxis guide `docs/how-to/run-autonomous-backlog-engine.md`.

- **Asset Forge Blackbox Test Suite Modular Decomposition (`TASK-0092`)**:
  - Decomposed monolithic `tests/test_blackbox_asset_forge.py` (421 lines) into two focused, single-responsibility suites:
    - `tests/test_blackbox_asset_forge_generation.py` (133 lines) covering battlemap and token procedural synthesis, spatial wall geometry extraction, transparency, and Silo S3 storage.
    - `tests/test_blackbox_asset_forge_auth_and_events.py` (231 lines) covering CloudEvents registry compliance, Redis Streams publication, SpiceDB Zanzibar authorization, asset metadata queries, and request bounds validation.
  - Enforced Hard Invariant 6 (< 500 lines limit) ensuring all asset forge test suites stay strictly under 250 lines.

### Added
- **Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover (`TASK-0055`, `PRD-0002`, `US-0025`, `US-0026`)**:
  - Implemented configurable tactical guardrail profiles on character aggregates (`StandInGuardrails`) supporting spell slot reservation limits, ally protection affinities, melee avoidance, and risk threshold flags.
  - Added REST endpoints `PUT /api/v1/characters/{id}/guardrails` and `GET /api/v1/characters/{id}/guardrails` in `services/character_sheet` secured via SpiceDB Zanzibar object authorization.
  - Implemented zero-HP permadeath safeguard aggregate invariant automatically stabilizing absent player characters at 0 HP without death save failures, emitting `StandInStabilized` over Redis Streams.
  - Added mid-session hot-swap takeover endpoint `POST /api/v1/sessions/{id}/hot-swap` in `services/game_session` transferring active token and turn control from AI stand-in to authenticating player in < 100ms with SpiceDB authorization while preserving combat round and initiative continuity.
  - Integrated tactical guardrails evaluation into The Watcher decision engine (`the_watcher` and `inference_worker`) with ally protection, spell slot conservation, melee disengagement, and humorous DM penalty flavor adaptation under "drunk" and "foolishness".
  - Defined and registered `StandInPolicyUpdated`, `StandInStabilized`, and `CharacterControlTransferred` CloudEvents across domain events packages.
  - Vendored Lit Web Component `<runefoble-stand-in-guardrails>` in `services/character_sheet/ui/` with interactive Storybook stories and `/ui/manifest` discovery.
  - Added Diataxis How-To guide (`docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`) and updated technical reference docs.
  - Added comprehensive blackbox TDD test suite (`tests/test_blackbox_stand_in_guardrails.py`).

- **DM Co-Pilot Whisper Prompts and Veto Override Engine (`TASK-0053`, `PRD-0001`, `US-0017`)**:
  - Implemented secure DM narrative suggestion stream in `the_watcher` providing atmospheric hints, monster tactics, and passive perception cues (`GET /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers`, `POST /api/v1/watcher/whispers/generate`).
  - Enforced SpiceDB Zanzibar authorization (`dungeon_master` relation, `run_session` permission) on all whisper queries, action vetoes, and approvals with 403 Forbidden rejection for unauthorized users.
  - Implemented pre-execution veto interceptor engine in `services/the_watcher` with configurable pause window (default 2000ms) for AI-proposed game actions (`POST /api/v1/watcher/actions/propose`).
  - Added one-click action veto endpoint (`POST /api/v1/watcher/veto`), immediate action approval (`POST /api/v1/watcher/approve`), and intent modification (`POST /api/v1/watcher/modify`).
  - Registered CloudEvents domain events: `WatcherActionProposed`, `WatcherActionVetoed`, `WatcherActionApproved`, `WatcherActionModified`, and `DMNarrativeWhispered`.
  - Implemented and vendored Lit Web Component `<runefoble-dm-whisper-bar>` in `@runefoble/the-watcher-ui` with Bauhaus tokens, action interceptor countdown banner, one-click veto/approve/edit controls, and Storybook stories.
  - Advertised `runefoble-dm-whisper-bar` in `the_watcher` `/ui/manifest`.
  - Added Diataxis How-To guide (`docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`) and updated technical reference docs (`docs/reference/events-schema.md`, `docs/reference/ports-and-endpoints.md`).
  - Added comprehensive blackbox TDD test suite (`tests/test_blackbox_dm_copilot.py`).
- **Conversational Target Disambiguation & Compound Action Intents (`TASK-0054`, `PRD-0001`, `US-0021`)**:
  - Implemented `DisambiguationEngine` in `services/the_watcher` detecting ambiguous entity references from spatial coordinates and entity tags with sub-400ms evaluation latency.
  - Implemented automated clarification prompt synthesis generating immersive audible and textual choices (e.g., *"Which goblin? The archer by the pillar or the shaman on the altar?"*).
  - Implemented `CompoundActionEngine` decomposing multi-clause spoken commands into ordered capability checks, movement, and attack nodes.
  - Added partial failure coordination with configurable rollback or partial success status handling if an intermediate check fails.
  - Added public HTTP frontdoor endpoints `POST /api/v1/watcher/intent/parse`, `POST /api/v1/watcher/intent/resolve`, and `POST /api/v1/watcher/intent/execute`.
  - Registered and published `IntentDisambiguationRequested`, `CandidateGhostPreviewEmitted`, and `CompoundActionResolved` CloudEvents over Redis Streams.
  - Added comprehensive blackbox TDD test suite (`tests/test_blackbox_intent_disambiguation.py`) verifying multi-target clarification, combo ordering, partial failure handling, and < 400ms SLA compliance.

- **Dynamic Soundscape & Adaptive Audio Microservice (`TASK-0050`, `PRD-0010`, `US-0039`)**:
  - Scaffolded new bounded context microservice `services/soundscape` with internal port `8009` and registered in UV monorepo workspace.
  - Implemented Encounter Tension Scoring Engine dynamically computing real-time tension (0–100) from combat rounds, enemy CR threat, and party health ratios.
  - Implemented Adaptive Audio Stem Mixer crossfading multi-track stems (`ambient`, `tension`, `combat`, `boss`) with smooth gain matrices.
  - Implemented WebAudio Ducking Coordinator muting/attenuating music layers by -12dB upon speech events (`PlayerSpokeEvent`) and tactical foley stingers.
  - Added tactical sound foley catalog and REST frontdoor (`POST /api/v1/soundscape/cue`) with preset audio URLs and volume gain controls.
  - Implemented event-sourced `SoundscapeAggregate` powered by `eventsource-py` handling `SoundscapeTrackChanged`, `SoundscapeCueTriggered`, `SoundscapeTensionUpdated`, `SoundscapeMoodOverridden`, and `SoundscapeDuckingToggled`.
  - Subscribed to `CombatStarted` and `CombatRoundAdvanced` over Redis Streams for autonomous encounter tension scoring and track transition.
  - Enforced SpiceDB Zanzibar authorization on manual DM mood overrides (`POST /api/v1/soundscape/override`).
  - Vendored Lit Web Component `<runefoble-soundscape-controls>` in `services/soundscape/ui/` with Bauhaus styling tokens, custom event contracts, Storybook stories, and `/ui/manifest` discovery.
  - Added Deployment, Service, and ConfigMap to umbrella Helm chart (`deployments/helm/runefoble/templates/soundscape.yaml`) and registered OpenAPI endpoint in Swagger UI.
  - Added Diataxis How-To guide (`docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`) and updated technical reference docs.
  - Added comprehensive blackbox TDD test suite (`tests/test_blackbox_soundscape.py`).
- **Roadmap & Creative Feature Pipeline Expansion (`Milestone 5`, `Milestone 6`)**:
  - Expanded `ROADMAP.md` to introduce Milestone 5 (*Collaborative Creation, Downtime & Tactile Immersion*) and Milestone 6 (*Intelligent Living Worlds & Spatial Multi-Party Universes*).
  - Expanded User Personas (`docs/project/user_stories/PERSONAS.md`) with three new creative archetypes:
    - **Rowan — The Chronicler & Worldbuilding Artisan**: Lorecrafter, diegetic artifact collector, and cartographer.
    - **Bram — The Tinkerer & Downtime Crafter**: Tactician, alchemical brewer, base builder, and tavern game gambler.
    - **Nadia — The Expressive Thespian & Performer**: Dramatic character roleplayer, musical leitmotif performer, and spell VFX caster.
  - Expanded Speculative Feature Inventory (`docs/project/product/FEATURE_INVENTORY.md`) across Domains 7-10:
    - Domain 7: Worldbuilding, In-World Artifacts & Living Codex (`FEAT-LRE-02`, `FEAT-LRE-03`, `FEAT-LRE-04`).
    - Domain 8: Downtime Activities, Social Minigames & Base Building (`FEAT-DWN-01`, `FEAT-DWN-02`, `FEAT-DWN-03`, `FEAT-DWN-04`).
    - Domain 9: Expressive Performance, Audio Leitmotifs & Particle VFX (`FEAT-EXP-01`, `FEAT-EXP-02`, `FEAT-EXP-03`).
    - Domain 10: Hybrid Tabletop & Tangible Maker (`FEAT-MAK-01`, `FEAT-MAK-02`).
  - Authored and accepted 7 new User Stories (`US-0044` through `US-0050`):
    - `US-0044`: Interactive Campfire Downtime and Alchemical Crafting.
    - `US-0045`: Generative In-World Handouts, Wax Seals and 3D Relic Inspector.
    - `US-0046`: Character Musical Leitmotifs and Dynamic Theme Scoring.
    - `US-0047`: Interactive Tavern Minigames, Gambling and Personality-Driven Merchant Haggling.
    - `US-0048`: Multi-Modal Kinetic Spell VFX and WebGL Particle Canvas.
    - `US-0049`: Printable Tabletop Forge: Grid-Calibrated PDFs, Standees and 3D STL Tokens.
    - `US-0050`: Collaborative Campaign Atlas and Multi-Layered Living Codex.
  - Authored and accepted 3 Product Requirement Records (`PRD-0014`, `PRD-0015`, `PRD-0016`):
    - `PRD-0014`: Downtime Activities, Alchemical Crafting & Party Stronghold Engine.
    - `PRD-0015`: Generative Diegetic Handouts, 3D Relic Inspector & Printable Tabletop Forge.
    - `PRD-0016`: Personal Character Leitmotifs, Wardrobe Gallery & Kinetic WebGL Spell VFX.
  - Integrated full feature pipeline into `docs/project/backlog/` (`TASK-0100` through `TASK-0106` in `proposed/`) and synchronized `PRIORITY.md` with optimal 10-item JIT refinement buffer.

- **Procedural Battlemap & Token Asset Forge Microservice (`TASK-0049`, `PRD-0009`, `US-0038`)**:
  - Scaffolded new bounded context microservice `services/asset_forge` with internal port `8008`.
  - Implemented procedural battlemap grid generator extracting line-of-sight wall segments, doors, and themed hazard pools (lava, acid, necrotic spikes).
  - Implemented procedural character and monster token portrait synthesizer with circular clipping and alpha transparency.
  - Integrated automated S3 storage upload with presigned URL generation via Silo (`SiloStorageService`).
  - Added spatial geometry projection payloads formatted directly for `board_state` mutators (`terrain_mutations`, `obstacle_tokens`).
  - Implemented `AssetForgeAggregate` powered by `eventsource-py` publishing `BattlemapForged` and `TokenAssetForged` CloudEvents over Redis Streams.
  - Added `forged_asset` definition to SpiceDB Zanzibar authorization schema (`runefoble.zed`).
  - Vendored Lit Web Component `<runefoble-asset-forge>` in `services/asset_forge/ui/` with Storybook stories and `/ui/manifest` endpoint.
  - Added Deployment, Service, and ConfigMap to umbrella Helm chart (`deployments/helm/runefoble/templates/asset-forge.yaml`).
  - Added Diataxis How-To guide (`docs/how-to/forge-procedural-battlemaps-and-tokens.md`) and reference updates.
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
- **Microfrontends Blackbox Test Suite Modular Decomposition (`TASK-0088`)**:
  - Decomposed `tests/test_microfrontends.py` (454 lines) into two focused, single-responsibility blackbox test suites:
    - `tests/test_microfrontend_manifests.py` (191 lines) covering service microfrontend discovery (`GET /ui/manifest`), component tag registries, package integrity, and battlemap uploader frontdoor contracts.
    - `tests/test_microfrontend_app_shell.py` (212 lines) covering App Shell Lit composition, workspace link declarations, Storybook story indexing, voice controls WebAudio/WebRTC specs, and companion style module decomposition invariants.
  - Removed original monolith `tests/test_microfrontends.py`.
  - Strictly enforced Hard Invariant 6 with both test files well under the 250-line ceiling and zero test regression across 450 passing tests.

  - Decomposed monolithic `libs/runefoble_auth/src/runefoble_auth/sync.py` into focused submodules:
    - `sync_tuples.py` (179 lines) covering `SyncResult` models, role normalization tables (`CAMPAIGN_ROLE_RELATIONS`, `normalize_campaign_role`), low-level write/delete helpers with retry execution, and batching/reconciliation utilities.
    - `sync_events.py` (127 lines) covering domain event and CloudEvent payload parsing (`extract_event_type`, `get_event_field`), unified dispatching (`handle_domain_event`), and granular entity handlers for `SessionCreated`, `ParticipantJoined`, `CharacterCreated`, and `TokenPlaced`.
    - `sync.py` (190 lines) retaining the `ZitadelSpiceDBSyncService` coordinator with 100% backward-compatible public methods and re-exports.
  - Added comprehensive test coverage in `tests/test_spicedb_client.py` (180 lines) covering client CRUD, tuple formatting, claims resolution, and event dispatching.
  - Strictly enforced Hard Invariant 6 (< 200 lines per file) across all modified and newly created modules.
- **SpiceDB Auth Sync Test Suite Decomposition (`TASK-0044`)**:
  - Decomposed monolithic test file `tests/test_blackbox_spicedb_zitadel_sync.py` (408 lines) into two focused, modular blackbox test suites:
    - `tests/test_blackbox_spicedb_identity_sync.py` (213 lines): covers user registration, Zitadel OIDC claim syncing, campaign GM/player role assignments, instant revocation, Redis Streams session deserialization, and transient fault resilience with exponential backoff retry.
    - `tests/test_blackbox_spicedb_ownership_sync.py` (210 lines): covers tactical board token movement isolation, spectator read-only inspection, domain event stream synchronization (`SessionCreated`, `ParticipantJoined`, `CharacterCreated`), character ownership revocation, and error handling for malformed event payloads.
  - Updated `gateway/api/src/gateway_api/auth_sync.py` to ensure `get_sync_service()` dynamically tracks the active SpiceDB client instance configured via `get_spicedb_client()`.
  - Strictly enforced Hard Invariant 6 with both test files well under the 250-line target ceiling and zero regression across 406 passing tests.
- **Autonomous DM Presets, Monster Templates, and Combat Tactics Modular Decomposition (`TASK-0062`)**:
  - Decomposed `services/the_watcher/src/the_watcher/autonomous_dm.py` into focused, single-responsibility submodules: `presets.py` (scene catalogs & atmosphere builders), `encounters.py` (CR balancing & monster templates), and `tactics.py` (tactical combat decision heuristics).
  - Maintained 100% backward-compatible facade `AutonomousDMEngine` and public re-exports in `autonomous_dm.py`.
  - Strictly enforced Hard Invariant 6 with all submodules and test files well under 170 lines.
- **Domain Aggregates and Rule Tables Modular Decomposition (`TASK-0060`)**:
  - Decomposed monolithic domain aggregate files across `character_sheet`, `board_state`, and `game_session` bounded contexts into focused `rules.py` (game balance tables, hazard formulas, spatial/initiative calculations) and `models.py` (Pydantic state schemas with immutable transition methods and request/response DTOs) submodules.
  - Maintained 100% backward-compatible re-exports in all `aggregate.py` modules.
  - Enforced Hard Invariant 6 with all modified and newly created modules strictly under 280 lines.
- **Modular Routers Blackbox Test Suite Modular Decomposition (`TASK-0090`)**: Decomposed monolithic `tests/test_blackbox_modular_routers.py` into three specialized bounded-context test suites (`tests/test_blackbox_watcher_routers.py`, `tests/test_blackbox_session_routers.py`, and `tests/test_blackbox_board_routers.py`), strictly enforcing Hard Invariant 6 (< 500 lines per file) with all suites well under 150 lines and preserving 100% test coverage across all 15 frontdoor routes and OpenAPI contracts.
- **PostgreSQL Event Store & Provisioning Test Suite Modular Decomposition (`TASK-0058`)**:
  - Decomposed `tests/test_blackbox_postgres_event_store.py` (419 lines) into two focused, modular test suites:
    - `tests/test_blackbox_postgres_provisioning.py` (133 lines) covering multi-database container initialization (`init-multidb.sh`), DSN normalization, asyncpg dialect reconciliation, and reachability probe fallbacks.
    - `tests/test_blackbox_postgres_event_store.py` (184 lines) covering schema auto-creation, cross-bounded-context aggregate persistence roundtrips (`GameSessionAggregate`, `CharacterAggregate`, `BoardAggregate`), optimistic concurrency control, and raw event stream inspection.
  - Extracted shared container fixtures and network helpers into `tests/helpers/postgres.py` (149 lines), registered globally via `tests/conftest.py` plugin architecture.
  - Strictly enforced Hard Invariant 6 with all files remaining well under the 500-line ceiling and zero test coverage loss.
- **Campaign Lore Retrieval Modular Decomposition (`TASK-0089`)**: Decomposed monolithic `services/campaign_lore/src/campaign_lore/retrieval.py` into focused submodules `extraction.py` (NER regexes, entity typing heuristics, `WorldbuildingLlmProvider`), `scoring.py` (Okapi BM25 tokenization, term frequency weighting, cosine similarity, Reciprocal Rank Fusion), `models.py` (data models), and a lean coordinator `retrieval.py` (`LoreRetrievalEngine` / `HybridLoreEngine`) preserving Hard Invariant 6 (< 500 lines) and 100% backward compatibility.
- **Backlog Engine Test Suite Modular Decomposition (`TASK-0087`)**: Decomposed monolithic `tests/test_pr_conflict_detection.py` into three specialized suites (`tests/test_backlog_ci_watcher.py`, `tests/test_backlog_stale_recovery.py`, and `tests/test_backlog_pr_repair.py`), strictly enforcing Hard Invariant 6 (< 500 lines per file) with all suites well under 160 lines.
- **Documentation Navigation**: Featured the Platform Showcase and Changelog in `zensical.toml` and the root documentation landing page (`docs/index.md`).
- **Build Automation**: Enhanced `scripts/build_docs.py` to synchronize `CHANGELOG.md` to `docs/changelog.md` during documentation compilation.

### Fixed
- **Project Visualizer Local Script Syntax & Favicon**: Fixed missing closing bracket in `agy_launcher.js` DOM listener causing `Uncaught SyntaxError` on local server, added automated Node.js syntax verification tests for all client scripts and bundles, and eliminated browser 404 console errors by handling `/favicon.ico` with 204 No Content and embedding an inline SVG dice icon.

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
