# Changelog

All notable changes to the Runefoble platform will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- **Board State Models and Pydantic Schemas Modular Decomposition (`TASK-0138`, `ADR-0003`, `ADR-0011`, `PRD-0003`, `PRD-0013`, `US-0012`, `US-0043`)**:
  - Decomposed `services/board_state/src/board_state/models.py` (433 lines) into focused, single-responsibility modules under `services/board_state/src/board_state/models/`:
    - `terrain.py`: Extracted `TerrainCellState`, `TerrainDict`, `ConfigureTerrainRequest`, and `VisibilityResponse` (< 70 lines).
    - `tokens.py`: Extracted `PlacedTokenState`, `PlaceTokenRequest`, `MoveTokenRequest`, and `MoveTokenResponse` (< 75 lines).
    - `vfx.py`: Extracted `BoardDecalState`, `CastSpellRequest`, `CastSpellResponse`, `FinishVFXRequest`, `FinishVFXResponse`, and `DecayDecalsRequest` (< 80 lines).
    - `actions.py`: Extracted token radial action and AoE template request/response schemas (< 25 lines).
    - `transitions.py`: Extracted `BoardTransitionsMixin` encapsulating all pure state mutation helpers (< 175 lines).
    - `board.py`: Extracted `BoardState`, `CreateBoardRequest`, `FogOfWarUpdateRequest`, and `UVTTImportResponse` (< 70 lines).
  - Maintained 100% backward compatibility with a lean facade re-export in `services/board_state/src/board_state/models.py` (< 70 lines) and `services/board_state/src/board_state/models/__init__.py`.
  - Added frontdoor blackbox test suite `tests/test_blackbox_board_state.py` verifying line length invariants (< 200 lines per file), backward-compatible facade re-exports, modular submodule imports, and BoardState transitions.

### Added
- **Campaign Analytics UI Blackbox Test Suite Modular Decomposition (`TASK-0143`, `ADR-0013`, `PRD-0012`, `US-0040`, `US-0054`)**:
  - Decomposed monolithic `tests/test_blackbox_campaign_analytics_ui.py` (383 lines) into focused, single-responsibility frontdoor blackbox test modules under `tests/test_blackbox_campaign_analytics_ui/` strictly adhering to Hard Invariant 6 (< 500 lines per file) with all resulting test files strictly under 160 lines.
  - Added `tests/test_blackbox_campaign_analytics_ui/conftest.py` (72 lines) isolating mock Redis, consumer group, event bus, storage, mock SpiceDB client, and worker fixtures.
  - Added `tests/test_blackbox_campaign_analytics_ui/test_analytics_dashboard_ui.py` (134 lines) verifying microfrontend manifest advertising, package metadata integrity, Storybook story coverage, and REST frontdoor MVP turn metrics delivery.
  - Added `tests/test_blackbox_campaign_analytics_ui/test_chronicle_timeline_ui.py` (135 lines) verifying `<runefoble-chronicle-timeline>` Custom Element decorator integrity, living chronicle milestone frontdoor binding, absentee recap metadata, milestone pagination limits, and session filtering.
  - Added `tests/test_blackbox_campaign_analytics_ui/test_spatial_heatmaps_ui.py` (155 lines) verifying `<runefoble-combat-heatmap>` Custom Element decorator, 2D canvas damage density calculations, coordinate cell overlays, metric filter parameters, and SpiceDB Zanzibar campaign object authorization.
  - Updated Diataxis guide `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` to document the modular blackbox test architecture.
- **Backlog Curation, JIT Refinement & Milestone 7 Roadmap Activation**:
  - Identified refactoring candidates approaching 500 lines (`tests/test_blackbox_caravan_contracts.py`, `services/game_session/src/game_session/routers/caravan_contracts.py`, `runefoble-caravan-board.ts`) and proposed decomposition tasks (`TASK-0146`, `TASK-0147`, `TASK-0148`).
  - Completed and closed Milestone 6 (Intelligent Living Worlds & Spatial Multi-Party Universes) across all 8 feature epics and microfrontends.
  - Activated Milestone 7 (Neural Audio Duplex & Tangible 3D Tabletop) with foundational platform and physics enablers (`TASK-0141`, `TASK-0150`) prioritized ahead of dependent UI epics (`TASK-0142`, `TASK-0149`).
  - JIT-refined 6 tasks (`TASK-0141`, `TASK-0144`, `TASK-0145`, `TASK-0146`, `TASK-0147`, `TASK-0150`) to maintain an optimal 10-item ready buffer in `docs/project/backlog/refined/` with zero specification drift.
- **Wardrobe Gallery Blackbox Test Suite Modular Decomposition (`TASK-0139`, `ADR-0013`)**:
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_wardrobe_gallery.py` (415 lines) into modular frontdoor test suites under `tests/test_blackbox_wardrobe_gallery/` strictly conforming to Hard Invariant 6 (< 500 lines per file, with all test files < 200 lines).
  - Added `tests/test_blackbox_wardrobe_gallery/test_wardrobe_api.py` (125 lines) verifying REST endpoints (`/api/v1/characters/{id}/portrait/active`, `/wardrobe`), object-level SpiceDB Zanzibar authorization checks, and microfrontend manifest advertisement.
  - Added `tests/test_blackbox_wardrobe_gallery/test_wardrobe_conditions.py` (114 lines) verifying HP threshold bloodied vignettes, poisoned auras, stunned visual markers, and condition removals.
  - Added `tests/test_blackbox_wardrobe_gallery/test_wardrobe_events.py` (173 lines) verifying generative wardrobe variant synthesis, Silo S3 binary asset persistence, and CloudEvents dispatching (`CharacterDamaged`, `PortraitVariantGenerated`, `CharacterPortraitUpdated`).
  - Added shared test configuration and frontdoor fixtures in `tests/test_blackbox_wardrobe_gallery/conftest.py` (49 lines).
  - Updated Diataxis guide `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md` with modular blackbox test architecture documentation.
- **Autonomous NPC Faction Agendas Radar & Intelligence Bulletin Microfrontend (`TASK-0137`, `ADR-0001`, `ADR-0006`, `ADR-0013`, `PRD-0001`, `PRD-0007`, `US-0057`)**:
  - Built and vendored `<runefoble-faction-radar>` Lit Web Component in `services/the_watcher/ui/src/runefoble-faction-radar.ts` with Bauhaus design tokens, interactive SVG radar chart visualizing multi-faction influence (0-100), territorial control chips, and disposition gauges.
  - Implemented confidential DM Intelligence Bulletin drawer detailing background faction clashes, territorial conquests, and strategic moves generated by the autonomous simulation engine.
  - Enforced SpiceDB Zanzibar object-level authorization (ADR-0001) in `GET /api/v1/campaigns/{id}/world-ticks/latest`, redacting private DM intelligence briefings from player participants while revealing public rumors and territory control.
  - Implemented diegetic Tavern Rumors & Street Whispers public feed displaying ambient world progression gossip to players and DMs.
  - Created modular styling in `services/the_watcher/ui/src/runefoble-faction-radar.styles.ts` adhering strictly to Bauhaus neobrutalism design tokens and Hard Invariant 6 (< 500 lines per file).
  - Registered and advertised `<runefoble-faction-radar>` in `services/the_watcher/ui/manifest.json` and through public frontdoor `GET /ui/manifest`.
  - Added Storybook stories in `services/the_watcher/ui/src/runefoble-faction-radar.stories.ts` with 5 scenarios (`Default`, `DMPrivateBriefing`, `PlayerPublicView`, `HighTensionWar`, `EmptyState`).
  - Authored comprehensive frontdoor blackbox TDD test suite `tests/test_blackbox_faction_radar_ui.py` validating manifest advertising, component exports, and Zanzibar redaction.
  - Updated Diataxis guide `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md`.
- **Cross-Campaign Caravan Trading & Frontier Bounty Board Microfrontend (`TASK-0136`, `ADR-0001`, `ADR-0006`, `ADR-0013`, `PRD-0007`, `US-0058`)**:
  - Implemented `<runefoble-caravan-board>` Lit Web Component in `services/game_session/ui/src/runefoble-caravan-board.ts` displaying active trade caravans, cargo manifests, escort contracts, payout bounties, transit route risk indicators, and real-time status notifications using Bauhaus design tokens.
  - Built Caravan Manifest Details Modal with detailed inspection view showing cargo inventory, departure settlement, destination stronghold, required collateral, and escort fee payout.
  - Built Active Transit Route Status Pill with visual progress bar showing remaining travel distance and ambush encounter alerts.
  - Implemented one-click "Accept Escort Contract" button triggering SpiceDB Zanzibar authorized REST call to `/api/v1/shared-worlds/{wid}/caravans/contracts/{cid}/accept` and optimistic UI updates.
  - Decomposed component into focused modules (`runefoble-caravan-types.ts`, `runefoble-caravan-modal.ts`, `runefoble-caravan-board.styles.ts`) strictly maintaining Hard Invariant 6 (<500 lines per file).
  - Registered and advertised `<runefoble-caravan-board>` via `/ui/manifest` and `/game_session/ui/manifest` in `services/game_session/src/game_session/main.py`.
  - Authored interactive Storybook stories in `services/game_session/ui/src/runefoble-caravan-board.stories.ts` with 6 scenarios (`DefaultNoticeBoard`, `ActiveCaravanTransit`, `AmbushWarningAlert`, `CaravanManifestModalOpen`, `GuildOfficerManagement`, `ContractPayoutFulfilled`).
  - Added comprehensive frontdoor blackbox test suite in `tests/test_blackbox_caravan_board_ui.py` validating manifest registration, component features, Storybook contract, and REST acceptance.
  - Updated Diataxis guide `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md`.
- **Spatial Companion Mobile WebRTC Audio & Haptic Controller Microfrontend (`TASK-0134`, `ADR-0002`, `ADR-0005`, `ADR-0013`, `PRD-0004`, `US-0059`)**:
  - Implemented responsive mobile companion Web Component `<runefoble-mobile-companion>` vendored in `services/voice_agent/ui/src/runefoble-mobile-companion.ts` with Bauhaus design tokens, active channel indicator, connection status pill, and large thumb-friendly push-to-talk button.
  - Implemented tactile haptic feedback dispatcher triggering `navigator.vibrate(pattern)` with graceful fallback for environments lacking vibration support, dispatching `haptic-pulse` CustomEvents.
  - Implemented diegetic secret whisper overlay with acoustic chime cue synthesized via WebAudio `AudioContext`, dismiss action, and privacy blur filter (`filter: blur(...)`) to prevent shoulder surfing.
  - Implemented low-bandwidth WebAudio stream controller with audio buffer health monitor (target 45ms), cellular stream profile indicators (`mobile_optimized`, `cellular_constrained`, `ultra_low`), and real-time network loss/bitrate gauges.
  - Registered and advertised `<runefoble-mobile-companion>` in `services/voice_agent/ui/manifest.json` and served via `/ui/manifest`.
  - Authored interactive Storybook stories in `services/voice_agent/ui/src/runefoble-mobile-companion.stories.ts` with 6 scenarios (`DefaultConnected`, `SecretWhisperActive`, `ConstrainedCellularFallback`, `TurnAlertPrompt`, `OfflineDisconnected`, `InteractiveSimulator`).
  - Added frontdoor blackbox test suite in `tests/test_blackbox_mobile_companion_ui.py` validating UI manifest registration, element contracts, and WebSocket frame dispatch.
  - Updated Diataxis guide `docs/how-to/connect-mobile-companion-and-haptic-gateway.md` and `docs/reference/microfrontend-architecture.md`.
- **Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts (`TASK-0129`, `ADR-0001`, `ADR-0006`, `ADR-0011`, `ADR-0013`, `PRD-0007`, `US-0058`)**:
  - Implemented event-sourced `CaravanContractAggregate` in `services/game_session/src/game_session/caravan.py` modeling cargo inventory, route risk level, transit stages, escort collateral, and reward gold/reputation with `@handles` methods for `CaravanContractPosted`, `CaravanContractAccepted`, `CaravanDispatched`, `CaravanAmbushed`, and `CaravanTradeFulfilled`.
  - Added public REST frontdoor notice board endpoints in `services/game_session/src/game_session/routers/caravan_contracts.py`: `POST /api/v1/shared-worlds/{id}/caravans/contracts`, `GET /api/v1/shared-worlds/{id}/caravans/contracts`, `GET /api/v1/shared-worlds/{id}/caravans/contracts/{cid}`, `POST /api/v1/shared-worlds/{id}/caravans/contracts/{cid}/accept`, `POST /api/v1/shared-worlds/{id}/caravans/contracts/{cid}/dispatch`, `POST /api/v1/shared-worlds/{id}/caravans/contracts/{cid}/ambush`, and `POST /api/v1/shared-worlds/{id}/caravans/contracts/{cid}/fulfill`.
  - Implemented dynamic settlement economy and merchant stock sync in `CaravanLedgerAggregate` updating workshop reagents, finished inventory, delivery statistics, and calculating dynamic price modifiers based on route delivery success rates.
  - Added SpiceDB Zanzibar schema definitions for `caravan_contract` in `libs/runefoble_auth/schema/runefoble.zed` and `MockSpiceDBClient`, enforcing that high-tier mercenary contracts require guild officer or party leader authorization.
  - Registered CloudEvents domain events `CaravanContractPosted`, `CaravanContractAccepted`, `CaravanAmbushed`, and `CaravanTradeFulfilled` in `libs/runefoble_events`.
  - Built vendored Lit Web Component microfrontend `<runefoble-caravan-board>` in `services/game_session/ui/src/runefoble-caravan-board.ts` with Bauhaus design tokens, interactive Storybook stories, and advertised via `/ui/manifest`.
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_caravan_contracts.py` with 100% frontdoor verification.
  - Updated Diataxis guide `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md` and `docs/reference/events-schema.md`.
- **Spatial Companion Mobile WebRTC Audio & Haptic Ping Gateway (`TASK-0128`, `ADR-0002`, `ADR-0005`, `ADR-0013`)**:
  - Implemented low-bandwidth adaptive Opus mono 16kHz audio stream profile in `services/voice_agent/src/voice_agent/mobile.py` optimizing cellular transmission over constrained network links.
  - Implemented automatic network degradation fallback across profile tiers (`mobile_optimized` at 16 kbps, `cellular_constrained` at 12 kbps, and `ultra_low` at 8 kbps) with Forward Error Correction (FEC) and Discontinuous Transmission (DTX).
  - Built dedicated WebSocket companion gateway at `/ws/mobile-companion/{session_id}` in `gateway_api.companion` enforcing SpiceDB Zanzibar authorization on connection.
  - Implemented haptic vibration framing protocols (triple-pulse `[200, 100, 200]` for secret DM whispers and double-pulse `[300, 150, 300]` for combat turn prompts) leveraging Web Vibration API.
  - Built diegetic lockscreen and app overlay notification formatters with recipient isolation ensuring private clues are withheld from other party members.
  - Added CloudEvents-compliant domain events `MobileCompanionConnected`, `MobileAudioProfileAdapted`, and `MobileHapticPingDispatched` registered in `libs/runefoble_events`.
  - Added REST frontdoor routes in `gateway_api/companion/router.py`: `POST /api/v1/mobile/companion/{session_id}/whisper`, `POST /api/v1/mobile/companion/{session_id}/turn-alert`, and `GET /api/v1/mobile/companion/profiles`.
  - Implemented `<runefoble-mobile-companion>` Lit Web Component in `services/voice_agent/ui/src/runefoble-mobile-companion.ts` with Bauhaus styling and interactive Storybook stories (`runefoble-mobile-companion.stories.ts`).
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_mobile_companion.py` and Diataxis guide `docs/how-to/connect-mobile-companion-and-haptic-gateway.md`.
- **West Marches Shared World Atlas Pins & Communal Stronghold Dashboard Microfrontend (`TASK-0135`, `ADR-0001`, `ADR-0006`, `ADR-0013`, `PRD-0007`, `PRD-0014`, `US-0050`, `US-0058`)**:
  - Built and vendored `<runefoble-west-marches-atlas>` Lit Web Component in `services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts` with Bauhaus design tokens, multi-party regional frontier map pins, layered milestone pins with danger ratings (1-5), and interactive popovers revealing discovering party attribution, date, and expedition notes.
  - Implemented Communal Stronghold Dashboard tab with facility status cards (Alchemical Workshop, Watchtower, Trading Post, Arcane Forge, Herbalist Sanctuary), dynamic shared rest boons and defensive buffers, and one-click facility upgrade actions.
  - Implemented Tavern Rumor Bulletin Board tab with filterable notice cards for expedition bounties, rumors, and party requests.
  - Implemented Cross-Campaign Expedition Chronicle log timeline displaying multi-party discovery history.
  - Enforced SpiceDB Zanzibar authorization (`shared_world` object permissions) scoping private discovery notes from rival parties while sharing tactical frontier map pins.
  - Implemented `WestMarchesAtlasAggregate` in `services/campaign_lore/src/campaign_lore/west_marches_aggregate.py` backed by `eventsource-py` and domain events `SharedWorldCreated`, `CampaignRegisteredToSharedWorld`, `CrossCampaignDiscoveryShared`, `OutpostEstablished`, `SharedStrongholdUpgraded`, and `CommunalNoticePosted`.
  - Added REST frontdoor router in `services/campaign_lore/src/campaign_lore/routers/west_marches.py` exposing `GET /api/v1/campaigns/{id}/west-marches`, `POST /api/v1/campaigns/{id}/west-marches/discoveries`, `POST /api/v1/campaigns/{id}/west-marches/stronghold/upgrade`, and `POST /api/v1/campaigns/{id}/west-marches/tavern-board/notices`.
  - Registered and advertised `<runefoble-west-marches-atlas>` in `services/campaign_lore/ui/manifest.json` and `GET /ui/manifest`.
  - Authored interactive Storybook stories in `services/campaign_lore/ui/src/runefoble-west-marches-atlas.stories.ts` with 5 scenarios (`DefaultFrontierView`, `CommunalStrongholdView`, `TavernNoticeBoardView`, `RestrictedPlayerView`, `GuildOfficerAdminView`).
  - Added frontdoor blackbox test suite in `tests/test_blackbox_west_marches_ui.py` and updated `tests/test_microfrontend_manifests.py`.
  - Updated Diataxis guide `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md` and `docs/reference/ports-and-endpoints.md`.
- **West Marches Shared Persistent World State & Cross-Campaign Registry (`TASK-0127`, `ADR-0001`, `ADR-0006`, `ADR-0011`, `PRD-0007`, `US-0058`)**:
  - Implemented event-sourced `SharedWorldAggregate` in `services/game_session/src/game_session/west_marches.py` managing common geographical map pins, shared outpost levels, and communal tavern notice boards.
  - Implemented `CaravanLedgerAggregate` in `services/game_session/src/game_session/caravan_ledger.py` managing scheduled resource caravan transit and regional settlement merchant stock ledgers.
  - Added CloudEvents domain events `SharedWorldCreated`, `CampaignRegisteredToSharedWorld`, `CrossCampaignDiscoveryShared`, `OutpostEstablished`, `SharedStrongholdUpgraded`, `CommunalNoticePosted`, `CaravanDispatched`, `CaravanTradeCompleted`, and `RegionalMerchantStockUpdated` registered in `libs/runefoble_events`.
  - Added public REST frontdoor endpoints in `services/game_session/src/game_session/routers/west_marches.py` and `caravan_trade.py`: `POST /api/v1/shared-worlds`, `GET /api/v1/shared-worlds/{id}`, `POST /api/v1/shared-worlds/{id}/campaigns`, `POST /api/v1/shared-worlds/{id}/discoveries`, `GET /api/v1/shared-worlds/{id}/discoveries`, `POST /api/v1/shared-worlds/{id}/outposts`, `POST /api/v1/shared-worlds/{id}/tavern-board/notices`, `GET /api/v1/shared-worlds/{id}/tavern-board/notices`, `POST /api/v1/shared-worlds/{id}/caravans/dispatch`, `POST /api/v1/shared-worlds/{id}/caravans/{id}/complete`, and `GET /api/v1/shared-worlds/{id}/outposts/{name}/merchant-stock`.
  - Updated SpiceDB Zanzibar authorization schema (`libs/runefoble_auth/schema/runefoble.zed`) and `MockSpiceDBClient` (`libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py`) defining `shared_world` object permissions (`guild_officer`, `participant`, `campaign->view/play`) while strictly isolating private character sheets and party whisper notes.
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_west_marches.py` verifying multi-campaign discovery synchronization, caravan trade unlocks, communal tavern boards, and Zanzibar isolation.
  - Authored Diataxis guide `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md` and updated `docs/reference/events-schema.md` and `AGENTS.md`.

- **Autonomous NPC Faction Agendas & Background Simulation Engine (`TASK-0126`, `ADR-0002`, `ADR-0006`, `ADR-0011`)**:
  - Implemented event-sourced `FactionAggregate` in `services/the_watcher/src/the_watcher/factions.py` tracking faction assets, influence (1-100), operational resources, disposition, and goal progress via `eventsource-py` (Hard Invariant 2).
  - Built `FactionSimulationEngine` in `services/the_watcher/src/the_watcher/simulation_engine.py` simulating probabilistic agenda checks based on rival counter-measures and regional stability modifiers.
  - Added DM Intelligence Bulletin generator in `bulletin.py` producing concise geopolitical briefings, territorial shifts, trade shortages, and evolving tavern rumors.
  - Added CloudEvents domain events `FactionCreated`, `FactionAgendaSet`, `FactionAgendaAdvanced`, `GeopoliticalShiftOccurred`, and `WorldTickExecuted` in `libs/runefoble_events`.
  - Added public REST frontdoor endpoints in `services/the_watcher/src/the_watcher/routers/factions.py`: `POST /api/v1/campaigns/{id}/world-tick` (alias: `POST /api/v1/campaigns/{id}/factions/tick`), `POST /api/v1/campaigns/{id}/factions`, `GET /api/v1/campaigns/{id}/factions`, `GET /api/v1/campaigns/{id}/factions/{id}`, and `GET /api/v1/campaigns/{id}/world-ticks/latest` with SpiceDB Zanzibar object authorization checks.
  - Updated SpiceDB authorization schema in `libs/runefoble_auth/schema/runefoble.zed` defining `faction` object permissions and fixing schema closing delimiter.
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_faction_simulation.py` with frontdoor setup.
  - Authored Diataxis guide `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md` and updated `docs/reference/ports-and-endpoints.md` and `docs/reference/events-schema.md`.
- **Multi-Modal Kinetic Spell VFX & WebGL Particle Magic (`TASK-0104`, `ADR-0004`, `ADR-0006`, `ADR-0012`, `ADR-0013`)**:
  - Implemented 60fps lightweight WebGL particle visual effects engine (`services/board_state/ui/src/particle_canvas.ts`) with GPU billboard instancing and graceful 2D canvas fallback.
  - Implemented spell archetype shaders and particle generators in `particle_archetypes.ts` and `particle_shaders.ts` for Evocation (firestorm, lightning chain arcs, frost bloom), Abjuration (rotating hexagonal arcane shield barrier), and Conjuration (dimensional portal swirl).
  - Integrated visual effects overlay into `<runefoble-tactical-board>` and `<runefoble-board>` with automatic canvas resizing via `ResizeObserver` and zero layout shift.
  - Added ephemeral grid decals (`scorched_earth`, `frost`, `lightning_scorch`, `abjuration_glyph`, `portal_residue`) naturally fading over 2 active combat rounds, powered by domain event `EphemeralDecalsDecayed`.
  - Added domain events `SpellCast`, `AreaEffectExploded`, `VFXAnimationFinished`, and `EphemeralDecalsDecayed` registered in `libs/runefoble_events`.
  - Added HTTP and WebSocket frontdoors in `services/board_state/src/board_state/routers/vfx.py` and `previews.py` delivering sub-150ms speech-to-VFX launch trajectories.
  - Enhanced The Watcher speech-to-intent action grammar to parse alphanumeric coordinates (e.g., "Fireball centered at coordinate D7").
  - Calibrated particle bloom luminance across dark, light, and high-contrast themes per ADR-0012.
  - Added interactive Storybook stories showcasing firestorm, lightning arc, and shield barrier animations with trigger buttons.
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_spell_vfx.py` and Diataxis how-to guide `docs/how-to/trigger-kinetic-spell-vfx-and-particles.md`.
- **Generative Character Wardrobe, Emotion & State Portrait Gallery (`TASK-0124`, `ADR-0003`, `ADR-0006`, `ADR-0013`)**:
  - Implemented dynamic Condition & Injury Overlay Engine in `services/character_sheet/src/character_sheet/portrait.py` applying real-time bloodied vignettes (<50% HP), poisoned auras, and stunned dizzy halos over base character portrait avatars.
  - Added generative wardrobe attire variant synthesis in `services/asset_forge/` (`routers/wardrobe.py` and `generator.py`) supporting thematic styles (`ballroom_masquerade`, `arctic_tundra`, `tavern_casual`, `battle_damaged`, `ceremonial`) preserving character facial embedding seeds, uploading to Silo S3 storage.
  - Implemented `<runefoble-wardrobe-gallery>` microfrontend Web Component in `services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts` with Bauhaus design tokens, active condition badge pills, outfit carousel, one-click avatar equipping, and interactive Storybook stories (`runefoble-wardrobe-gallery.stories.ts`).
  - Added new CloudEvents-compliant domain events `CharacterDamaged`, `PortraitVariantGenerated`, and `CharacterPortraitUpdated` (alias: `PortraitAssigned`) in `libs/runefoble_events`.
  - Added modular `wardrobe_router.py` to `character_sheet` exposing `/api/v1/characters/{id}/portrait` and `/api/v1/characters/{id}/wardrobe` endpoints with SpiceDB Zanzibar authorization checks.
  - Added comprehensive frontdoor blackbox test suite `tests/test_blackbox_wardrobe_gallery.py` verifying condition badge triggers, asset storage, event stream dispatch, and SpiceDB object permissions.
  - Authored Diataxis guide `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md` and updated `docs/reference/events-schema.md`.

### Changed
- **Board State AoE Templates Geometry and Rendering Modular Decomposition (`TASK-0140`, `ADR-0013`)**:
  - Decomposed `services/board_state/ui/src/aoe_templates.ts` (411 lines) into modular, single-responsibility TypeScript modules adhering strictly to ADR-0013 and Hard Invariant 6 (< 200 lines per module).
  - Extracted type contracts, AoE shape definitions, event payloads, and color design tokens into `services/board_state/ui/src/aoe_types.ts` (41 lines).
  - Extracted pure mathematical intersection algorithms for cones, spheres, lines, and cubes into `services/board_state/ui/src/aoe_geometry.ts` (94 lines).
  - Extracted CSS styles, SVG template shape generation, and interactive rotation/origin handles into `services/board_state/ui/src/aoe_canvas.ts` (132 lines).
  - Maintained backward-compatible coordinator facade `<runefoble-aoe-template>` in `services/board_state/ui/src/aoe_templates.ts` (99 lines), re-exporting all types, geometry math, and rendering utilities.
  - Updated Diataxis guide `docs/how-to/interact-with-radial-action-menu-and-aoe-templates.md`.
- **Backlog Curation, Tech Debt Scanning & JIT Ready Buffer Replenishment (`TASK-0134`, `TASK-0135`, `TASK-0136`, `TASK-0137`, `TASK-0138`, `TASK-0139`, `TASK-0140`, `TASK-0141`, `TASK-0142`, `TASK-0143`, `TASK-0144`, `TASK-0145`)**:
  - Audited repository health and file length invariants, identifying refactoring candidates in `services/board_state/src/board_state/models.py` (433 lines), `tests/test_blackbox_wardrobe_gallery.py` (415 lines), `services/board_state/ui/src/aoe_templates.ts` (411 lines), `libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` (410 lines), and `tests/test_blackbox_west_marches.py` (402 lines).
  - Proactively proposed and refined modular decomposition tasks `TASK-0138`, `TASK-0139`, `TASK-0140`, `TASK-0143`, `TASK-0144`, and `TASK-0145` to prevent breaching Hard Invariant 6 (< 500 lines).
  - Synchronized `docs/project/backlog/ROADMAP.md` Milestone 2 (confirming all foundational enablers complete), Milestone 5 (updating to Complete with `TASK-0125`), Milestone 6 (updating to Current with `TASK-0126`, `TASK-0127`, and new microfrontend epics), and established Milestone 7 for future horizon tabletop capabilities.
  - Replenished ready buffer in `docs/project/backlog/refined/` to optimal buffer of 10 items (`TASK-0128`, `TASK-0129`, `TASK-0134`, `TASK-0135`, `TASK-0136`, `TASK-0137`, `TASK-0138`, `TASK-0139`, `TASK-0140`, `TASK-0143`), citing governing ADRs, PRDs, and testable frontdoor blackbox definitions of done.
  - Added new persona-driven user stories `US-0060` (Zero-Latency Neural Voice Duplex) and `US-0061` (3D Miniature Tokens & Tabletop Physics) and registered them in `docs/project/user_stories/REGISTRY.md`.
  - Re-indexed `docs/project/backlog/PRIORITY.md` following lean engineering hierarchy: Enablers → Current Milestone Epics → Identified Refactorings → Future Milestones.
- **Board State Aggregate Mutation Handlers and Event Appliers Modular Decomposition (`TASK-0133`, `ADR-0003`, `ADR-0006`, `ADR-0011`)**:
  - Decomposed `services/board_state/src/board_state/aggregate.py` from 488 lines down to 140 lines by extracting domain command mutation handlers and `@handles` event state appliers into modular mixins under `services/board_state/src/board_state/handlers/`.
  - Extracted token placement, movement kinematics, difficult terrain traversal, and path hazard triggers into `TokensHandlerMixin` (`services/board_state/src/board_state/handlers/tokens.py`, 145 lines).
  - Extracted Chebyshev visibility, party-wide sight union, and fog-of-war revelation/shrouding into `FogHandlerMixin` (`services/board_state/src/board_state/handlers/fog.py`, 75 lines).
  - Extracted rotatable AoE spell templates, WebGL kinetic VFX animations, and ephemeral combat decals into `VFXHandlerMixin` (`services/board_state/src/board_state/handlers/vfx.py`, 118 lines).
  - Extracted tactical radial token actions into `ActionsHandlerMixin` (`services/board_state/src/board_state/handlers/actions.py`, 57 lines).
  - Preserved 100% backward compatibility for all public methods, properties, and `@handles` registrations on `BoardAggregate`, strictly enforcing Hard Invariant 6 with all handler submodules strictly under 160 lines and coordinator facade at 140 lines.
  - Added comprehensive frontdoor blackbox test suite `tests/test_blackbox_tactile_board.py` validating token lifecycle, movement, hazards, radial actions, and event-sourced aggregate reload.
  - Updated Diataxis guide `docs/how-to/define-event-sourced-aggregates.md` documenting modular aggregate decomposition patterns for `BoardAggregate`.
- **Character Sheet Microfrontend Styles Modular Decomposition (`TASK-0123`, `ADR-0004`, `ADR-0012`, `ADR-0013`)**:
  - Decomposed `services/character_sheet/ui/src/runefoble-character-sheet.styles.ts` (394 lines) into discrete CSS modules: `runefoble-character-sheet.core.styles.ts` (132 lines), `runefoble-character-sheet.inventory.styles.ts` (125 lines), and `runefoble-character-sheet.conditions.styles.ts` (150 lines), with companion alias modules (`core.styles.ts`, `inventory.styles.ts`, `conditions.styles.ts`).
  - Reduced `runefoble-character-sheet.styles.ts` to a 28-line aggregator combining the modular CSS blocks into a typed `CSSResultGroup`.
  - Exposed modular style subpaths in `@runefoble/character-sheet-ui` package manifest and FastAPI `/ui/manifest` frontdoor.
  - Verified visual rendering and Storybook builds with zero errors across light and dark modes.
  - Updated blackbox TDD test suite `tests/test_blackbox_character_sheet_ui.py` to enforce style module thresholds (<180 lines per module, <40 lines aggregator, strictly obeying Hard Invariant 6).
- **Particle Canvas Decals and Projectile Physics Modular Decomposition (`TASK-0132`, `ADR-0004`, `ADR-0006`, `ADR-0012`, `ADR-0013`)**:
  - Decomposed `services/board_state/ui/src/particle_canvas.ts` from 492 lines down to 254 lines by extracting ballistic projectile physics and trail calculation into `particle_projectiles.ts` (121 lines) and ephemeral combat grid decal lifecycle and opacity decay into `particle_decals.ts` (100 lines).
  - Streamlined `WebGLParticleEngine` to focus exclusively on WebGL program initialization, buffer management, and the 60fps main animation loop, strictly adhering to Hard Invariant 6 (< 500 lines per file; all files < 260 lines).
  - Re-exported modular projectile and decal classes (`ProjectileManager`, `DecalManager`) and physics functions across `particle_canvas.ts` and `services/board_state/ui/src/index.ts`.
  - Updated blackbox TDD test suite `tests/test_blackbox_spell_vfx.py` verifying module extraction, exports, and line limit invariants.
  - Updated Diataxis guide `docs/how-to/trigger-kinetic-spell-vfx-and-particles.md` with modular architecture breakdown.
- **Wardrobe Gallery Styles and Sub-Components Modular Decomposition (`TASK-0131`, `ADR-0004`, `ADR-0009`, `ADR-0012`, `ADR-0013`)**:
  - Decomposed `services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts` from 401 lines down to 185 lines by extracting its extensive CSS stylesheet block into dedicated module `services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts` (246 lines), maintaining strict compliance with Hard Invariant 6 (< 500 lines per file; both modules < 250 lines).
  - Isolated condition badge, variant card, active section, and attire forging sub-renderers in `RunefobleWardrobeGallery` component.
  - Advertised companion styles module via `@runefoble/character-sheet-ui/runefoble-wardrobe-gallery.styles`, exported in `src/index.ts`, and declared in `/ui/manifest`.
  - Updated blackbox test suite `tests/test_blackbox_wardrobe_gallery.py` and `tests/test_microfrontend_app_shell.py` to verify modular styles extraction and file length invariants.
  - Updated Diataxis guide `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md` with modular architecture details.
- **Character Leitmotifs Blackbox Test Suite Modular Decomposition (`TASK-0130`, `ADR-0002`, `ADR-0003`, `ADR-0006`, `ADR-0009`, `ADR-0010`, `ADR-0013`)**:
  - Decomposed monolithic `tests/test_blackbox_character_leitmotifs.py` (437 lines) into discrete, single-responsibility blackbox test suites strictly conforming to Hard Invariant 6 (< 500 lines) and all resulting test files strictly under 200 lines.
  - Added `tests/test_blackbox_leitmotif_events.py` (99 lines) verifying CloudEvents domain event class mapping and payload serialization roundtrips.
  - Added `tests/test_blackbox_leitmotif_api.py` (160 lines) verifying REST API endpoints, SpiceDB Zanzibar character owner authorization, and `<runefoble-leitmotif-config>` microfrontend manifest and component invariants.
  - Added `tests/test_blackbox_leitmotif_triggers.py` (174 lines) verifying multi-modal triggers (critical hits, death saves, voice ducking) and volume envelope stage calculations.
  - Added shared test fixture and frontdoor helper utilities in `tests/helpers/leitmotif_fixtures.py`.
  - Updated Diataxis guide `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` to reflect the modular test architecture.
- **Backlog Curation, Tech Debt Scanning & JIT Ready Buffer Replenishment (`TASK-0129`, `TASK-0130`, `TASK-0131`, `TASK-0132`, `TASK-0133`)**:
  - Audited codebase health and file length invariants, identifying `tests/test_blackbox_character_leitmotifs.py` (437 lines), `tests/test_project_visualizer.py` (415 lines), `services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts` (401 lines), `services/board_state/src/board_state/aggregate.py` (488 lines), and `services/board_state/ui/src/particle_canvas.ts` (492 lines) as refactoring candidates approaching the 500-line invariant limit.
  - Proactively proposed and refined modular decomposition tasks `TASK-0132` (particle canvas projectiles and decals extraction) and `TASK-0133` (board state aggregate mutation handlers and event appliers decomposition) to prevent breaches of Hard Invariant 6 (< 500 lines).
  - Verified `docs/project/backlog/ROADMAP.md` Milestone 2 (confirming all foundational enablers complete) and updated Milestone 5 completed status for `TASK-0102`, `TASK-0104`, and `TASK-0124`.
  - Added `TASK-0129` to Milestone 6 in `ROADMAP.md`.
  - JIT-refined `TASK-0129` (Cross-Campaign Caravan Trading Ledgers), `TASK-0130` (Character Leitmotifs Test Suite Decomposition), `TASK-0131` (Wardrobe Gallery Styles Decomposition), `TASK-0132` (Particle Canvas Physics Decomposition), and `TASK-0133` (Board State Aggregate Handlers Decomposition) into `docs/project/backlog/refined/`, establishing complete Definitions of Ready with governing ADRs, PRDs, user stories, and testable blackbox DoDs.
  - Replenished ready buffer in `docs/project/backlog/refined/` to the optimal target buffer of 10 items.
  - Re-indexed `docs/project/backlog/PRIORITY.md` maintaining strict prioritization: Enablers → Current Milestone Epics → Identified Refactorings → Future Milestones.
- **PRD Pipeline Test Suite Modular Decomposition (`TASK-0121`, `ADR-0003`, `ADR-0009`)**:
  - Decomposed monolithic `tests/test_prd_pipeline.py` (418 lines) into discrete, single-responsibility test modules with shared fixture helpers in `tests/helpers/prd_fixtures.py`.
  - Added `tests/test_prd_pipeline_manager.py` (81 lines) covering `PRDManager` lifecycle, directory structures, buffer audits, and registry index synchronization.
  - Added `tests/test_prd_pipeline_planner.py` (137 lines) covering `DecompositionPlanner`, architectural spike keyword detection, UI/worker heuristics, and dependency graph sequencing.
  - Added `tests/test_prd_pipeline_decomposer.py` (141 lines) covering `PRDDecomposer` execution facade, counter resolution, `PlanWriter` file persistence, and task template formatting.
  - Added `tests/test_prd_pipeline_cli.py` (92 lines) covering CLI subcommands, error exits on missing PRD IDs, and shell script interface wrappers.
  - Kept all decomposed test modules strictly below 150 lines (and < 250 lines), upholding Hard Invariant 6 with zero regressions across 13 passing test cases.
  - Updated Diataxis guide `docs/how-to/decompose-prds-into-vertical-slices.md`.

- **Project Visualizer Test Suite Modular Decomposition (`TASK-0122`, `ADR-0003`, `ADR-0009`)**:
  - Decomposed monolithic `tests/test_project_visualizer.py` (416 lines) into three focused, single-responsibility test suites: `tests/test_visualizer_parser.py` (210 lines), `tests/test_visualizer_graph.py` (110 lines), and `tests/test_visualizer_server.py` (123 lines).
  - Maintained 100% test coverage and backwards compatibility across all visualizer capabilities, verifying entity extraction across personas/ADRs/PRDs/stories/tasks, git commit & PR harvesting, deterministic cache fingerprinting, graph edge construction, buffer metrics, PRD-story-task traceability support, zoom & minimap bundles, HTTP endpoints, static asset resolution, CLI subcommands, and codebase line-length invariants.
  - Enforced strict line limit invariants with all decomposed test suites strictly under 250 lines and well below Hard Invariant 6 (< 500 lines per file).

- **Backlog Curation, Tech Debt Scanning & JIT Ready Buffer Replenishment (`TASK-0102`, `TASK-0104`, `TASK-0121`, `TASK-0122`, `TASK-0123`, `TASK-0124`, `TASK-0125`, `TASK-0126`, `TASK-0127`, `TASK-0128`)**:
  - Audited repository health and file length invariants, identifying refactoring candidates in `tests/test_prd_pipeline.py` (417 lines), `tests/test_project_visualizer.py` (415 lines), and `services/character_sheet/ui/src/runefoble-character-sheet.styles.ts` (394 lines).
  - Proactively proposed and refined modular decomposition tasks `TASK-0121`, `TASK-0122`, and `TASK-0123` to prevent breaching Hard Invariant 6 (< 500 lines).
  - Synchronized `docs/project/backlog/ROADMAP.md` Milestone 2 (confirming all foundational enablers complete) and Milestone 5 (updating completed checkboxes for `TASK-0101`, `TASK-0103`, `TASK-0105`, `TASK-0106`).
  - Replenished ready buffer in `docs/project/backlog/refined/` to optimal buffer of 10 items (`TASK-0102`, `TASK-0104`, `TASK-0121`, `TASK-0122`, `TASK-0123`, `TASK-0124`, `TASK-0125`, `TASK-0126`, `TASK-0127`, `TASK-0128`), citing governing ADRs, PRDs, and testable frontdoor blackbox definitions of done.
  - Added new persona-driven user stories `US-0055` through `US-0059` and registered them in `docs/project/user_stories/REGISTRY.md`.
  - Re-indexed `docs/project/backlog/PRIORITY.md` following lean engineering hierarchy: Enablers → Current Milestone Epics → Identified Refactorings → Future Milestones.
  - Moved completed `TASK-0066` to `complete/` with status Complete.
- **Theming Tokens and Contrast Invariants Test Suite Modular Decomposition (`TASK-0114`, `ADR-0004`, `ADR-0009`, `ADR-0012`)**:
  - Decomposed monolithic `tests/test_theming.py` (443 lines) into two focused, specialized test modules: `tests/test_theming_tokens.py` (174 lines) and `tests/test_theming_contrast.py` (178 lines), preventing breaches of Hard Invariant 6 (< 500 lines).
  - Maintained 100% backward compatibility and test coverage across semantic token hierarchies, themes.css modular `@import` resolution, index.css and index.html loads, `<runefoble-theme-switcher>`, Storybook preview matrix, WCAG 2.1 AA/AAA contrast ratios, zero-hardcoded-hex invariants in Web Component styles, and settings modal style modular decomposition.
  - Enforced strict line limit invariants with both resulting test files strictly under 180 lines (< 200 lines limit).
  - Updated design tokens and themes documentation in `docs/reference/design-tokens-and-themes.md`.
- **Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition (`TASK-0113`, `ADR-0003`, `ADR-0011`)**:
  - Decomposed monolithic `services/character_sheet/src/character_sheet/aggregate.py` (342 lines) into modular command mutation handlers and `@handles` event state applier sub-modules under `services/character_sheet/src/character_sheet/handlers/`: `inventory.py` (62 lines) for equipment slots and inventory items, `spells.py` (103 lines) for level progression and spell slots, `vitals.py` (138 lines) for health modifications, conditions, absence penalties, and stand-in guardrails, and coordinator facade `aggregate.py` (87 lines).
  - Maintained 100% backward compatibility for all methods and event handlers on `CharacterAggregate` and re-exported models, rules, and constants.
  - Enforced strict file length limits with all sub-modules under 140 lines and well below the 200 lines limit, protecting Hard Invariant 6 (< 500 lines).
  - Added comprehensive test suites `tests/test_character_sheet.py` and `tests/test_blackbox_character_inventory.py` verifying public frontdoors, event store reconstitution, and structural line-length invariants.
  - Updated Diataxis guide `docs/how-to/define-event-sourced-aggregates.md`.
- **Stand-In AI Persona Decision Engine and Tactical Policy Modular Decomposition (`TASK-0112`, `ADR-0002`, `ADR-0003`, `ADR-0006`)**:
  - Decomposed monolithic `services/the_watcher/src/the_watcher/stand_in_ai.py` (344 lines) into specialized, single-responsibility sub-modules: `stand_in_guardrails.py` (127 lines) for tactical policy evaluation, `stand_in_persona.py` (138 lines) for humorous penalty and personality simulation, `stand_in_recap.py` (94 lines) for absentee chronicle recap generation, and `stand_in_ai.py` (64 lines) lightweight facade.
  - Preserved 100% backward compatibility for all public methods on `StandInAIEngine` and public entrypoints.
  - Enforced strict file length limits with all sub-modules under 140 lines and well below the 200 lines limit, protecting Hard Invariant 6 (< 500 lines).
  - Added comprehensive blackbox TDD test suite `tests/test_blackbox_stand_in_guardrails.py` validating frontdoor HTTP endpoints, tactical guardrails, and structural invariants.
  - Updated Diataxis how-to guide `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`.
- **Project Visualizer Parser Modular Decomposition (`TASK-0059`, `ADR-0003`)**:
  - Decomposed monolithic `tools/project_visualizer/parser.py` (461 lines) into dedicated sub-parsers in `tools/project_visualizer/parsers/`: `adr_parser.py` (75 lines), `product_parser.py` (155 lines), `persona_parser.py` (93 lines), `backlog_parser.py` (158 lines), `graph_builder.py` (20 lines), and `markdown_utils.py` (89 lines).
  - Maintained 100% backward compatibility via `tools/project_visualizer/parser.py` facade (141 lines) and `tools/project_visualizer/markdown_utils.py` facade (21 lines) with re-exported classes and entrypoints (`ProjectParser`, `scan_project`, `build_traceability_graph`).
  - Enforced strict file length limits with all modules strictly under 200 lines, protecting Hard Invariant 6 (< 500 lines).
  - Added modular parser compatibility and line-length invariant tests in `tests/test_project_visualizer.py` and updated Diataxis documentation in `docs/how-to/visualize-project-content.md`.
- **Backlog Triage and JIT Ready Buffer Replenishment (`TASK-0059`, `TASK-0101`, `TASK-0103`, `TASK-0105`, `TASK-0112`, `TASK-0113`, `TASK-0114`, `TASK-0119`, `TASK-0120`)**:
  - JIT-refined 9 tasks across Milestone 5 feature epics and invariant-prevention modular decompositions, replenishing ready buffer to 10 items.
  - Proposed and refined modular decompositions for `tools/prd_pipeline/decomposer.py` (`TASK-0119`) and `frontend/src/styles/themes.css` (`TASK-0120`).
  - Synchronized `PRIORITY.md`, `ROADMAP.md` Milestone 5 completion checkboxes, and PRD acceptance links with zero status drift.
- **CSS Design Tokens and Theme Variables Modular Decomposition (`TASK-0120`, `ADR-0004`, `ADR-0009`, `ADR-0012`)**:
  - Decomposed monolithic `frontend/src/styles/themes.css` (424 lines) into modular CSS sub-modules under `frontend/src/styles/themes/`: `base.css` (universal radii, typography, spacing, transitions, and z-indexes), `bauhaus.css` (Bauhaus Modernist light/dark tokens and contrast borders), `dark-fantasy.css` (gothic stone and obsidian shadow palettes), `parchment.css` (weathered manuscript, warm sepia, and iron gall ink tokens), and `cyber-rune.css` (neon cyan, grid wireframe, and ultraviolet tokens).
  - Maintained 100% backward compatibility via `frontend/src/styles/themes.css` root bundle (12 lines) importing sub-modules via standard CSS `@import` rules with zero breaking changes to existing `--rf-*` tokens.
  - Enforced strict line limit invariants with all resulting stylesheets strictly under 150 lines (< 90 lines for base, < 150 lines for themes, < 40 lines for root bundle), protecting Hard Invariant 6 (< 500 lines).
  - Extended frontdoor test suite in `tests/test_theming.py` and `tests/test_settings_modal.py` with recursive `@import` resolution and modular decomposition verification.
  - Updated design tokens documentation in `docs/reference/design-tokens-and-themes.md`.


### Added
- **Radial Token Action Menu & Rotatable AoE Spell Templates (`TASK-0125`, `PRD-0013`, `US-0056`, `ADR-0004`, `ADR-0006`, `ADR-0013`)**:
  - Implemented interactive contextual radial action dial `<runefoble-radial-menu>` blooming in under 120ms with Bauhaus geometric icons for Attack, Dash, Disengage, Dodge, and Cast.
  - Implemented rotatable geometric AoE spell engine `<runefoble-aoe-template>` supporting 15ft/30ft cones (53.13° spread angle), spheres (10ft, 20ft radius), and lines (5ft x 30ft/60ft) with tactile 15-degree angular snapping.
  - Implemented live target intersection calculations highlighting affected tokens with glowing red/amber halos (`.target-halo`) and tinted grid cells at 60fps across square and hex grids.
  - Added event-sourced CloudEvents domain events: `TokenActionExecuted`, `AoETemplatePlaced`, and `AoETemplateRemoved` on `BoardAggregate`.
  - Added REST endpoints (`/tokens/{token_id}/action`, `/aoe/evaluate`, `/aoe/place`, `/aoe/{template_id}`) and real-time WebSocket stream handling for live AoE dragging and radial actions.
  - Registered `<runefoble-radial-menu>` and `<runefoble-aoe-template>` in `services/board_state/ui/` and `/ui/manifest`.
  - Added Storybook stories showcasing radial menu blooming and rotatable cone/sphere spell template placement.
  - Authored comprehensive blackbox test suite `tests/test_blackbox_radial_menu_and_aoe.py` and Diataxis how-to guide `docs/how-to/interact-with-radial-action-menu-and-aoe-templates.md`.

- **Personal Character Leitmotifs & Adaptive Musical Signatures (`TASK-0102`, `PRD-0016`, `US-0046`, `ADR-0002`, `ADR-0006`, `ADR-0010`, `ADR-0013`)**:
  - Implemented personalized character leitmotif profile modeling (`leitmotif.py`) supporting five instrument timbres (`lute`, `brass`, `woodwind`, `strings`, `synth`), tempo multiplier scaling, and triumphant/somber audio stem URLs.
  - Implemented adaptive audio layering engine with sub-250ms dynamic stinger triggering on clutch criticals (`CriticalHitScored`, `DiceRolled(is_crit=True)`) and near-death saves (`DeathSaveStarted`).
  - Implemented smooth volume envelope generator with configurable attack, sustain, and release curves preventing audio clipping.
  - Integrated WebAudio sidechain compressor applying -12dB attenuation to active leitmotif stems during human speech activity (`PlayerSpokeEvent` or `/duck`).
  - Added event-sourced CloudEvents domain events: `LeitmotifProfileConfigured`, `LeitmotifTriggered`, `CriticalHitScored`, and `DeathSaveStarted`.
  - Built and vendored `<runefoble-leitmotif-config>` Lit microfrontend in `services/soundscape/ui/src/` with instrument timbre selector, tempo/volume sliders, audition buttons with WebAudio earcon synthesis, and Storybook stories.
  - Authored comprehensive blackbox TDD test suite `tests/test_blackbox_character_leitmotifs.py` and updated Diataxis how-to guide `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` and reference `docs/reference/events-schema.md`.

- **Collaborative Campaign World Atlas & Living Party Codex (`TASK-0106`, `PRD-0015`, `US-0050`, `ADR-0001`, `ADR-0003`, `ADR-0006`, `ADR-0011`, `ADR-0013`)**:
  - Implemented interactive multi-layered world atlas engine (`atlas.py`) with deep-zoom coordinate projections across continental, regional, and municipal layers, ray-casting territory polygon containment, and contested boundary detection.
  - Implemented event-sourced `AtlasAggregate` and `CodexAggregate` tracking geographical markers, geopolitical boundary shifts, and journal entry revisions with CloudEvents domain events (`AtlasPinCreated`, `AtlasPinUpdated`, `AtlasLayerToggled`, `AtlasTerritoryUpdated`, `CodexEntryPublished`, `CodexEntryUpdated`).
  - Implemented automated entity cross-referencing against the `campaign_lore` redstring knowledge graph (`codex.py`), generating illuminated markdown bodies with inline hyperlinking to NPC and location nodes.
  - Enforced fine-grained SpiceDB Zanzibar object authorization (`codex_entry#author`, `codex_entry#editor`, `party_shared`, `public`) ensuring private player notes remain strictly protected from unauthorized party members.
  - Built and vendored `<runefoble-campaign-atlas>` Lit microfrontend in `services/campaign_lore/ui/src/` with canvas pan/zoom viewport, Bauhaus pin markers, filter drawer, and codex sidebar; accompanied by Storybook stories and registered in `/ui/manifest`.
  - Authored comprehensive blackbox test suite in `tests/test_blackbox_campaign_atlas.py` and Diataxis how-to guide `docs/how-to/interact-with-campaign-atlas-and-codex.md`.

- **PRD Decomposer Planning and Slice Generation Modular Decomposition (`TASK-0119`, `ADR-0003`)**:
  - Decomposed monolithic `tools/prd_pipeline/decomposer.py` into an orchestrator facade (`decomposer.py`, 78 lines), planning engine (`planner.py`, 157 lines), markdown templating module (`templates.py`, 137 lines), and slice templates (`slice_templates.json`), preventing violations of Hard Invariant 6 (< 500 lines).
  - Maintained 100% backward compatibility for all `PRDDecomposer` methods (`plan_decomposition`, `execute_decomposition`, `get_max_task_number`, `get_max_story_number`) and private creation/heuristic delegates.
  - Refactored `PlanWriter` in `tools/prd_pipeline/writer.py` (39 lines) to delegate frontmatter and body formatting to `templates.py`.
  - Added comprehensive blackbox and unit test coverage in `tests/test_prd_pipeline.py` and updated Diataxis guide `docs/how-to/decompose-prds-into-vertical-slices.md`.

- **Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens (`TASK-0105`, `PRD-0015`, `US-0049`, `ADR-0003`, `ADR-0005`, `ADR-0010`, `ADR-0013`)**:
  - Implemented multi-page vector/raster PDF battlemap generator (`pdf_tiler.py`) calibrated to exact 1-inch physical tabletop grids (72pt) across Letter/A4 pages with alignment crosshairs and margin cut guides at 300 DPI.
  - Implemented papercraft standee sheet formatter (`standees.py`) generating print-ready folding paper miniatures with mirrored front/back artwork, character nameplates, HP tracking slots, and foldable base tabs.
  - Implemented procedural 3D STL mesh generator (`stl_generator.py`) producing mathematically watertight (2-manifold, $V - E + F = 2$) binary and ASCII STL miniature bases (28mm and 50mm) featuring snap-in status condition clips (Poisoned, Stunned, Blessed, Blinded).
  - Built and vendored `<runefoble-print-forge>` Lit microfrontend in `services/asset_forge/ui/src/` with interactive previews, paper size selectors, Bauhaus design tokens, and Storybook stories; registered in `/ui/manifest`.
  - Added public frontdoor HTTP routes `POST /assets/print-pdf` (alias: `/api/v1/forge/print-pdf`), `POST /assets/standees` (alias: `/api/v1/forge/standees`), and `POST /assets/stl-token` (alias: `/api/v1/forge/stl-token`) backed by Silo S3 storage and SpiceDB Zanzibar authorization.
  - Emitted CloudEvents 1.0 domain events `PrintPdfForged` and `StlTokenForged` and recorded state updates in `AssetForgeAggregate`.
  - Authored comprehensive blackbox test suite in `tests/test_blackbox_print_forge.py` and Diataxis how-to guide `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md`.

- **Interactive Tavern Minigames & Personality-Driven Merchant Haggling (`TASK-0103`, `PRD-0014`, `US-0047`, `ADR-0003`, `ADR-0006`, `ADR-0011`, `ADR-0013`)**:
  - Implemented turn-based Liar's Dice wagering, card tournaments, and drinking contests with progressive intoxication stages and dynamic voice DSP slurred speech filters (`VoiceDSPPipeline`).
  - Implemented personality-driven NPC merchant haggling featuring dynamic temperament state machines, mood meters, price curves, counter-offers, and reactive voice lines.
  - Published CloudEvents 1.0 domain events on Redis Streams (`MinigameStarted`, `MinigameTurnTaken`, `MinigameEnded`, `IntoxicationLevelChanged`, `HagglingNegotiated`).
  - Built and vendored `<runefoble-tavern-parlor>` Lit microfrontend in `services/game_session/ui/src/` with interactive 3D cup/dice shaker animations, Bauhaus tokens, and Storybook stories.
  - Exposed REST endpoints on `game_session` and `gateway_api` enforced by SpiceDB Zanzibar authorization (`session` / `campaign` `play` / `participate`).
  - Authored comprehensive blackbox test suite in `tests/test_blackbox_tavern_and_haggling.py` and Diataxis guides in `docs/how-to/` and `docs/reference/`.

- **Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector (`TASK-0101`, `ADR-0003`, `ADR-0006`, `ADR-0010`, `ADR-0013`)**:
  - Implemented generative diegetic handout engine synthesizing weathered parchment textures, stylized calligraphy, breakable wax seals with acoustic audio cues, and secret UV-reactive invisible ink layer.
  - Implemented interactive 3D WebGL relic inspector (`RelicSynthesizer`) with orbit rotation, PBR metallic shaders, and clickable engraved rune hitboxes.
  - Built event-sourced aggregates `DiegeticHandoutAggregate` and `RelicAggregate` with domain events `HandoutGenerated`, `WaxSealBroken`, `InvisibleInkRevealed`, `RelicForged`, `RelicInspected`, and `RelicRuneTranslated`.
  - Added public frontdoor HTTP routes `/api/v1/lore/handouts` and `/api/v1/lore/relics` protected by SpiceDB Zanzibar authorization.
  - Created and vendored Lit Web Components `<runefoble-handout-viewer>` and `<runefoble-relic-inspector>` with Storybook stories in `@runefoble/campaign-lore-ui` and registered in `/ui/manifest`.
  - Authored Diataxis how-to guide `docs/how-to/inspect-diegetic-handouts-and-3d-relics.md` and reference `docs/reference/diegetic-handouts-and-relics-events.md`.

- **Settings Modal Styles and Sub-Component CSS Modular Decomposition (`TASK-0111`, `ADR-0004`, `ADR-0009`, `ADR-0012`, `ADR-0013`)**:
  - Decomposed monolithic `frontend/src/components/runefoble-settings-modal.styles.ts` into single-responsibility Lit CSS sub-modules in `frontend/src/components/styles/`: `settings-modal-layout.styles.ts`, `settings-modal-tabs.styles.ts`, and `settings-modal-controls.styles.ts`.
  - Maintained 100% backward compatibility via composite export in `runefoble-settings-modal.styles.ts` (28 lines) combining `[layoutStyles, tabsStyles, controlsStyles]`.
  - Preserved 100% visual consistency and WCAG 2.1 AA tokenized styling across all settings tab panels in Storybook.
  - Added modular decomposition and strict line budget verification tests in `tests/test_theming.py`, `tests/test_settings_modal.py`, and `tests/test_settings_subcomponents.py`.
  - Updated Diataxis how-to and reference guides in `docs/how-to/configure-appearance-and-themes.md` and `docs/reference/design-tokens-and-themes.md`.

- **Campaign Analytics Storage and Query Modular Decomposition (`TASK-0118`, `ADR-0003`, `ADR-0005`, `ADR-0011`)**:
  - Decomposed `storage.py` into storage facade (165 lines) and specialized query modules (`spatial.py`, `mvp.py`, `timeline.py`).
  - Maintained 100% backward compatibility for all public methods and aliases on `CampaignAnalyticsStorage`.
  - Added modular decomposition and line budget tests in `tests/test_campaign_analytics_storage_modular_decomposition.py`.

- **Stream Overlay Router and HUD Templates Modular Decomposition (`TASK-0117`, `ADR-0001`, `ADR-0004`, `ADR-0007`, `ADR-0013`)**:
  - Decomposed monolithic `gateway/api/src/gateway_api/routers/overlay.py` into single-responsibility modules strictly under 200 lines (`overlay.py`, `overlay_models.py`, and `overlay_templates.py`).
  - Extracted Pydantic wire models (`PartyMemberVitals`, `RollAnimationData`, `PartyVitalsData`) and `sanitize_party_vitals` helper into `gateway_api/overlay_models.py`.
  - Extracted alpha-transparent HTML/CSS HUD template generator and client-side WebSocket synchronization logic into `render_overlay_html` and `render_obs_overlay_html` in `gateway_api/overlay_templates.py`.
  - Maintained complete backward compatibility and public route contracts for `GET /overlay/party-vitals/{session_id}` and `WS /ws/overlay/{session_id}` while exposing `/overlay/ws/{session_id}` endpoint alias.
  - Added comprehensive frontdoor blackbox test suite in `tests/test_overlay_modular_decomposition.py` and updated Diataxis documentation.

- **Speech Intent Parser and Action Grammar Extractors Modular Decomposition (`TASK-0069`, `ADR-0002`, `ADR-0003`)**:
  - Decomposed `services/the_watcher/src/the_watcher/movement_parser.py` into `grammars.py` (93 lines), `spatial.py` (52 lines), and `movement_parser.py` (178 lines).
  - Extracted compiled regular expressions and lexical token sets into `grammars.py`, and tactical spatial math, vector conversions, and grid coordinate clamping into `spatial.py`.
  - Retained `SpeechIntentParser` coordinator with 100% backward-compatible public methods and class-level pattern access.
  - Authored comprehensive test suites in `tests/test_movement_parser.py` and `tests/test_blackbox_the_watcher.py`, and updated Diataxis documentation.

- **Campaign Analytics Worker and Event Dispatch Modular Decomposition (`TASK-0116`, `ADR-0003`, `ADR-0006`, `ADR-0011`)**:
  - Decomposed `services/campaign_analytics/src/campaign_analytics/worker.py` into asynchronous worker core `worker.py` (171 lines) and event projection dispatcher `event_handlers.py` (222 lines) with `event_helpers.py` (24 lines).
  - Isolated Redis Streams consumer group polling and worker lifecycle loops from domain event translation and spatial tracking state.
  - Extracted event projection handlers for spatial movements, combat rounds, health changes, dice rolls, and chronicle recaps.
  - Preserved 100% backward-compatible public contract on `CampaignAnalyticsWorker`, added tests in `tests/test_campaign_analytics_modular_decomposition.py`, and updated Diataxis documentation.

- **Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls (`TASK-0109`, `PRD-0010`, `US-0039`, `US-0053`, `ADR-0003`, `ADR-0004`, `ADR-0006`, `ADR-0007`, `ADR-0013`)**:
  - Vendored `<runefoble-soundscape-controls>` Lit Web Component in `services/soundscape/ui/` with Bauhaus tokens and strict Shadow DOM encapsulation.
  - Implemented multi-channel stem sliders (`melody`, `percussion`, `drone`, `ambient`) and master volume controls emitting `soundscape-volume` and `soundscape-stem-volume` events.
  - Implemented tactile soundboard grid with customizable foley preset buttons (`thunder`, `door_slam`, `steel_clash`, `roar`, `fireball`, `shield_block`) and client-side synthesized WebAudio earcon acoustic feedback.
  - Implemented WebAudio ducking coordinator managing -12dB attenuation triggered by voice activity and tactical cues.
  - Exposed service microfrontend manifest at `GET /ui/manifest` and `services/soundscape/ui/manifest.json`.
  - Added App Shell forwarding export in `frontend/src/components/runefoble-soundscape-controls.ts` and re-exported in `frontend/src/index.ts`.
  - Authored frontdoor blackbox test suite in `tests/test_blackbox_soundscape_ui.py` and updated Diataxis documentation in `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`.

- **Downtime Activities, Alchemical Crafting & Party Stronghold Engine (`TASK-0100`, `PRD-0014`, `US-0044`, `ADR-0001`, `ADR-0003`, `ADR-0006`, `ADR-0011`, `ADR-0013`)**:
  - Implemented `CraftingAggregate` modeling reagent affinity, catalytic stabilization, and volatile mishap risk matrices emitting `CraftingAttempted`, `CraftingSucceeded`, and `CraftingMishapOccurred`.
  - Implemented `StrongholdAggregate` and Campfire Rest sequence supporting multi-tier base upgrades, passive campaign resting boons, and collaborative storytelling prompts.
  - Added SpiceDB Zanzibar permissions in `runefoble.zed` and protected REST routes via API Gateway.
  - Vendored Lit Web Component `<runefoble-campfire-crafting>` in `services/game_session/ui/src/` with interactive Storybook stories, Bauhaus tokens, `/ui/manifest` discovery, blackbox tests, and Diataxis guide.

- **Character Sheet UI Inventory Grid and Condition Indicator Microfrontend (`TASK-0107`, `ADR-0003`, `ADR-0004`, `ADR-0007`, `ADR-0013`)**:
  - Developed and vendored `<runefoble-character-sheet>` Lit Web Component in `services/character_sheet/ui/` with Bauhaus geometric tokens and Shadow DOM encapsulation.
  - Implemented interactive paper doll slots emitting `equip-item`/`unequip-item` events and dynamic encumbrance capacity progress bar color-coded by load thresholds.
  - Implemented condition indicator badges distinguishing 5e rules conditions and absence penalties (`drunk`, `foolishness`) with interactive mechanics tooltips.
  - Implemented spellbook and spell slot tracker with clickable pips across tiers 1–9, daily prepared spell list, and known spellbook management.
  - Exposed service microfrontend manifest at `GET /ui/manifest`, forward export in App Shell, blackbox tests in `tests/test_blackbox_character_sheet_ui.py`, and Diataxis how-to guide.

- **Rules Compendium Search & Encounter Builder Microfrontend (`TASK-0108`, `PRD-0008`, `ADR-0001`, `ADR-0003`, `ADR-0004`, `ADR-0007`, `ADR-0013`)**:
  - Vendored `<runefoble-rules-compendium>` Lit Web Component in `services/rules_compendium/ui/` with Bauhaus geometric tokens and Shadow DOM encapsulation.
  - Implemented `<runefoble-rules-lookup>` delivering debounced sub-50ms hybrid BM25 and vector search across SRD monsters, spells, and conditions with category filter pills.
  - Implemented `<runefoble-encounter-builder>` computing dynamic party XP thresholds, real-time lethality brackets, and 1-click automated encounter balancing.
  - Provided Homebrew Forge form modal for custom creatures and spells, exported manifest at `GET /ui/manifest`, added tests, and updated Diataxis guide.

- **WebRTC Client Voice Service and Peer Connection Mesh Modular Decomposition (`TASK-0068`, `ADR-0002`, `ADR-0004`, `ADR-0009`, `ADR-0013`)**:
  - Decomposed `frontend/src/services/webrtc-voice.ts` into single-responsibility modules strictly under 200 lines (`webrtc-types.ts`, `webrtc-peer-mesh.ts`, and `webrtc-voice.ts`).
  - Preserved full backward compatibility for all imports and public service contracts via re-exports.
  - Added comprehensive blackbox test suite in `tests/test_blackbox_webrtc_client.py` and updated architecture documentation in `docs/explanation/realtime-voice-and-board-sync.md`.

- **Spectator Stream Overlay and Broadcast Test Suite Modular Decomposition (`TASK-0075`, `ADR-0001`, `ADR-0003`, `ADR-0004`, `ADR-0007`, `ADR-0009`, `ADR-0013`)**:
  - Decomposed monolithic `tests/test_spectator_view.py` into `test_spectator_events_and_schema.py` and `test_spectator_stream_overlay.py` validating spectator endpoints, tokens, and WebSockets.
  - Added endpoint aliases `/api/v1/spectator/sessions/{session_id}` and `/ws/spectator/{session_id}` in `gateway_api/routers/spectator.py`.

- **Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend (`TASK-0110`, `ADR-0003`, `ADR-0004`, `ADR-0007`, `ADR-0011`, `ADR-0013`)**:
  - Vendored `<runefoble-campaign-analytics>` Lit Web Component in `services/campaign_analytics/ui/` with Bauhaus geometric tokens and Shadow DOM encapsulation.
  - Implemented `<runefoble-combat-heatmap>` rendering canvas-based 2D tactical grid overlays with movement corridors and density metric filters.
  - Implemented `<runefoble-chronicle-timeline>` living chronicle scrubber with round stepping, auto-playback, and audio recap triggers.
  - Implemented party performance infographics featuring SVG/CSS token distribution bar charts and MVP achievement badges.
  - Exported service discovery manifest at `GET /ui/manifest`, added blackbox test suite in `tests/test_blackbox_campaign_analytics_ui.py`, and updated Diataxis guide `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`.

- **PRD Creation, Maintenance, and Task Decomposition Pipeline (`tools/prd_pipeline`, `scripts/decompose-prds.sh`, `ADR-0003`, `ADR-0013`)**:
  - Implemented modular PRD pipeline engine in `tools/prd_pipeline/` with CLI entrypoint `tools.prd_pipeline.cli` and executable shell wrapper `scripts/decompose-prds.sh`.
  - Added automated auditing (`audit`) and standardized PRD scaffolding (`create`) with automatic registration into `docs/project/product/REGISTRY.md`.
  - Built decomposition engine (`decomposer.py`) breaking PRDs into granular, single-pass tasks (architectural spikes, domain aggregates, APIRouters with SpiceDB Zanzibar checks, Lit microfrontends, and asynchronous Redis Streams workers).
  - Built bidirectional registry synchronizer (`registry_sync.py`) reconciling PRD, User Story, and Backlog Priority registries, repairing stale task references, and indexing new tasks in `docs/project/backlog/PRIORITY.md`.
  - Added Antigravity agent decomposition prompt generator and Makefile targets (`make prd-audit`, `make prd-decompose`, `make prd-create`, `make prd-sync`).
  - Authored comprehensive blackbox test suite in `tests/test_prd_pipeline.py` and Diataxis how-to guide `docs/how-to/decompose-prds-into-vertical-slices.md`.

- **Redis Streams Consumer Group Worker and Session Projections Modular Decomposition (`TASK-0076`, `ADR-0003`, `ADR-0006`, `ADR-0009`, `ADR-0011`)**:
  - Decomposed `libs/runefoble_platform/src/runefoble_platform/consumer_group.py` into dedicated event deserialization module `event_deserializer.py`, in-memory mock client `mock_redis.py`, and core worker `consumer_group.py`.
  - Preserved W3C trace context (`traceparent`, `tracestate`) across payload deserialization and domain event instantiation.
  - Decomposed `services/game_session/src/game_session/projections.py` into modular sub-package (`models.py`, `initiative.py`, `presence.py`, `appliers.py`, `session.py`).
  - Added unit and blackbox test coverage in `tests/test_game_session_projections.py` and updated technical reference `docs/reference/redis-streams-event-bus.md`.

- **Universal VTT Importer and Dynamic MCP Tool Registry (`TASK-0057`, `ADR-0007`, `ADR-0008`, `ADR-0010`, `ADR-0013`)**:
  - Implemented Universal VTT (`.dd2vtt`) parser in `services/board_state/src/board_state/parsers/uvtt.py` extracting grid resolution, line-of-sight wall vectors, door portals, ambient lights, and embedded base64 map imagery.
  - Built ingestion endpoint `POST /api/v1/board/{id}/import/uvtt` (alias: `/api/v1/boards/{id}/import/uvtt`) supporting both multipart file uploads and raw JSON payloads.
  - Automatically decoded map textures and persisted into Silo S3 (`battlemaps/`), binding `background_image_url` and `background_asset_id` to board aggregates.
  - Projected line-of-sight wall segments and populated obstacle bounds tokens across tactical boards.
  - Registered and published `UniversalVTTImported` (`runefoble.events.board.map_imported`) event, handled via eventsource-py `@handles` appliers.
  - Implemented Dynamic FastMCP Tool Registry (`gateway/mcp/src/gateway_mcp/dynamic_registry.py`) enabling runtime registration, schema validation, and deregistration of custom LLM tools without gateway restarts.
  - Enforced AST-level execution sandboxing rejecting forbidden system imports (`os`, `subprocess`, `sys`), dangerous builtins (`open`, `eval`, `exec`), and dunder attributes.
  - Exposed administrative REST endpoints (`/mcp/tools`, `/mcp/tools/{name}`, `/mcp/tools/{name}/execute`) on both `gateway_mcp` and `gateway_api`.
  - Added comprehensive blackbox TDD test suite in `tests/test_blackbox_uvtt_import.py` asserting multipart file ingestion, wall projection, Silo S3 persistence, and dynamic FastMCP execution.
  - Published Diataxis how-to guide `docs/how-to/import-universal-vtt-maps-and-register-dynamic-tools.md` and updated technical references.

- **Campaign Analytics & Chronicle Archive Microservice (`TASK-0052`, `ADR-0001`, `ADR-0003`, `ADR-0005`, `ADR-0006`, `ADR-0011`, `ADR-0013`)**:
  - Implemented `services/campaign_analytics` bounded context microservice to project combat telemetry, tactical damage heatmaps, party MVP turn statistics, and interactive campaign milestone timelines from Redis Streams domain events into PostgreSQL.
  - Built `CampaignAnalyticsWorker` consuming Redis Streams consumer group `campaign_analytics_worker` across `runefoble.events.session`, `runefoble.events.board`, `runefoble.events.character`, and `runefoble.events.watcher`.
  - Implemented event-sourced `CampaignChronicleAggregate` (`eventsource-py`) handling `ChronicleMilestoneRecorded`, `CombatTelemetrySnapshotCreated`, and `EncounterMvpAwarded`.
  - Added REST APIRouters guarded by SpiceDB Zanzibar object authorization (`permission="view"` on campaign):
    - `GET /api/v1/analytics/campaigns/{id}/heatmap`: Aggregated spatial coordinate hit/damage densities and lethality scoring.
    - `GET /api/v1/analytics/campaigns/{id}/mvp`: Per-encounter and campaign-level MVP awards (damage dealer, lifesaver, crits) with individual combatant stats.
    - `GET /api/v1/analytics/campaigns/{id}/timeline`: Chronological session milestones, boss defeats, and story recaps.
  - Exposed service discovery manifest (`GET /ui/manifest`), health check (`GET /healthz`), and OpenAPI aggregation (`GET /openapi.json`).
  - Added umbrella Helm deployment manifest `campaign-analytics.yaml` on internal port 8011 with Swagger UI aggregation and ingress routing.
  - Authored Diataxis How-To guide `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` and updated technical reference specifications.
  - Verified full test suite through frontdoor blackbox tests in `tests/test_blackbox_campaign_analytics.py` with zero file invariant violations (< 500 lines per file).

- **Cinematic Director Auto-Camera and OBS Stream Overlay (`TASK-0056`, `ADR-0001`, `ADR-0004`, `ADR-0007`, `ADR-0013`)**:
  - Implemented autonomous Cinematic Director virtual camera (`gateway_api.cinematic_director`) tracking active turn events (`TurnStarted`) and action centers (`TokenMoved`) with smooth cubic-bezier easing (`cubic-bezier(0.25, 0.1, 0.25, 1.0)`) within 300ms.
  - Exposed OBS transparent stream overlay route `GET /overlay/party-vitals/{session_id}` serving alpha-transparent canvas (`rgba(0, 0, 0, 0)`) with zero DM secret leakage (100% exclusion of hidden traps, unrevealed monster HP numbers, and DM notes).
  - Built real-time spectator WebSocket feed at `/ws/overlay/{session_id}` streaming sanitized party vitals, roll animations, and camera target updates.
  - Vendored `<runefoble-spectator-overlay>` Lit Web Component in `services/game_session/ui/src/` with Bauhaus design tokens, interactive Storybook stories, and advertised via `services/game_session/ui/manifest.json`.
  - Added blackbox TDD test suite in `tests/test_blackbox_cinematic_director.py` and Diataxis How-to guide in `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md`.

- **Backlog Curation, Invariant Health Protection, and Milestone 4 JIT Buffer Replenishment (`ADR-0009`)**:
  - Audited repository file lengths against Hard Invariant 6 (< 500 lines); verified zero violations across 600+ source files.
  - Preemptively proposed 4 modular decomposition tasks in `docs/project/backlog/proposed/` for files approaching limit:
    - TASK-0111: Settings Modal Styles and Sub-Component CSS Modular Decomposition (`frontend/src/components/runefoble-settings-modal.styles.ts` [356 lines]).
    - TASK-0112: Stand-In AI Persona Decision Engine and Tactical Policy Modular Decomposition (`services/the_watcher/src/the_watcher/stand_in_ai.py` [344 lines]).
    - TASK-0113: Character Sheet Aggregate Mutation Handlers and Event Appliers Decomposition (`services/character_sheet/src/character_sheet/aggregate.py` [342 lines]).
    - TASK-0114: Theming Tokens and Contrast Invariants Test Suite Modular Decomposition (`tests/test_theming.py` [332 lines]).
  - Replenished ready buffer in `docs/project/backlog/refined/` from 2 to exactly 10 items (JIT queue health) with rigorous blackbox TDD Definitions of Done, governing ADR citations, and INVEST validation:
    - TASK-0056: Cinematic Director Auto-Camera and OBS Stream Overlay.
    - TASK-0052: Campaign Analytics & Chronicle Archive Microservice.
    - TASK-0057: Universal VTT Importer and Dynamic MCP Tool Registry.
    - TASK-0110: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend.
    - TASK-0097: OpenPanel Analytics Blackbox Test Suite Modular Decomposition.
    - TASK-0076: Redis Streams Consumer Group Worker and Session Projections Modular Decomposition.
    - TASK-0068: WebRTC Client Voice Service and Peer Connection Mesh Modular Decomposition.
    - TASK-0070: Missing Player AI Stand-In and Absentee Recap Test Suite Modular Decomposition.
    - TASK-0071: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition.
    - TASK-0075: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition.
  - Synchronized `ROADMAP.md` Milestone 4 Foundational Platform Enabler (`TASK-0051`).
  - Re-indexed `docs/project/backlog/PRIORITY.md` and repaired traceability cross-links across accepted PRDs.
- **Character Sheet Modular Router and Schemas Decomposition (`TASK-0077`, `ADR-0003`, `ADR-0009`, `ADR-0011`)**:
  - Decomposed monolithic `services/character_sheet/src/character_sheet/main.py` into dedicated Pydantic request schema module `schemas.py` (77 lines), modular endpoint router `router.py` (162 lines), shared dependencies and mutation helpers `dependencies.py` (155 lines), and lean application entrypoint `main.py` (75 lines).
  - Maintained 100% backward compatibility for all REST endpoints (`/api/v1/characters`, `/api/v1/characters/{id}/level-up`, `/api/v1/characters/{id}/spells/prepare`, `/api/v1/characters/{id}/spells/cast`, `/api/v1/characters/{id}/health`, `/api/v1/characters/{id}/penalties`, `/api/v1/characters/{id}/inventory/add`, `/api/v1/characters/{id}/equipment`, `/api/v1/characters/{id}/conditions`, `/api/v1/characters/{id}/guardrails`, `/healthz`, `/ui/manifest`).
  - Added comprehensive blackbox router verification suite in `tests/test_blackbox_character_routers.py` verifying public frontdoors, OpenAPI registration, and Hard Invariant 6 / task line limits (< 180 lines per module).

- **TypeScript Audience Studio & Live Stream Interactivity Microservice (`TASK-0051`, `ADR-0001`, `ADR-0003`, `ADR-0005`, `ADR-0006`, `ADR-0007`, `ADR-0013`)**:
  - Implemented `services/audience_studio` as a first-class TypeScript microservice (Node.js / Fastify / TypeScript) for live streaming audience interactivity without table gameplay latency.
  - Built high-concurrency Audience Poll Engine supporting live chaos polls, time window expiration, multi-platform spectator vote ingestion (Twitch, YouTube, web), and quorum calculations.
  - Implemented SpiceDB Zanzibar-guarded DM moderation approval queue and live bidirectional WebSocket stream (`/ws/audience/{campaign_id}`) for real-time chaos modifier approval/veto.
  - Registered and published CloudEvents 1.0 specifications: `AudiencePollStarted`, `AudienceVoteCast`, `AudiencePollCompleted`, `AudienceModifierProposed`, and `AudienceModifierApproved`.
  - Vendored Lit microfrontend `<runefoble-audience-studio>` (`@runefoble/audience-studio-ui`) featuring Bauhaus tokens, Shadow DOM encapsulation, and Storybook stories.
  - Exposed service discovery manifest (`GET /ui/manifest`) and OpenAPI documentation hub specification (`GET /openapi.json`).
  - Added umbrella Helm deployment manifest `audience-studio.yaml` with Traefik ingress routing and Swagger UI hub integration.
  - Authored Diataxis How-To guide `docs/how-to/orchestrate-audience-chaos-polls.md` and updated technical reference specifications.
  - Verified full test suite through frontdoor blackbox tests in `tests/test_blackbox_audience_studio.py` and `tests/test_blackbox_audience_studio_auth.py` with zero file invariant violations (< 250 lines per file).
- **Full Traceability Matrix and PRD Story/Task Support Enrichment**:
  - Increased support across under-supported PRDs by authoring dedicated user stories and backlog tasks:
    - US-0051: Character Level Progression, Spellbook Preparation & Spell Slot Scaling (`PRD-0006`).
    - US-0052: Homebrew Spell, Monster & Rule Template Authoring (`PRD-0008`).
    - US-0053: DM Manual Soundboard Triggers and Tactical Foley Overrides (`PRD-0010`).
    - US-0054: Post-Session Combat Spatial Heatmaps and Party Damage Analytics (`PRD-0012`).
    - TASK-0107: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend (`PRD-0006`, `<runefoble-character-sheet>`).
    - TASK-0108: Rules Compendium Search & Encounter Builder Microfrontend (`PRD-0008`, `<runefoble-rules-compendium>`).
    - TASK-0109: Dynamic Soundscape Mixing Panel Microfrontend and WebAudio Ducking Controls (`PRD-0010`, `<runefoble-soundscape-controls>`).
    - TASK-0110: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend (`PRD-0012`, `<runefoble-campaign-analytics>`).
  - Added `Governing PRD` column to `docs/project/user_stories/REGISTRY.md` mapping all 54 user stories to their parent PRD.
  - Enriched all 16 PRD records in `docs/project/product/accepted/` with explicit `## Linked User Stories` and `## Implementing Backlog Tasks` markdown sections.
  - Enhanced `tools/project_visualizer/parser.py` and `graph.py` to support case-insensitive entity linking, frontmatter-declared relationships (`governing_prds`, `governing_stories`), and bidirectional PRD-to-task synchronization, boosting total traceability graph edges to 786 with zero orphaned stories or unlinked PRDs.
  - Added verification invariant test `test_all_prds_have_stories_and_tasks_support` in `tests/test_project_visualizer.py`.
- **Backlog Curation, Invariant Invariant Protection, and Milestone 4 JIT Triage (`ADR-0009`)**:
  - Identified source files approaching Hard Invariant 6 limits (>400 lines) and created preemptive modular decomposition proposals:
    - TASK-0093: DM Co-Pilot Router and Blackbox Test Suite Modular Decomposition (`tests/test_blackbox_dm_copilot.py` [474 lines], `copilot.py` [399 lines]).
    - TASK-0094: Intent Disambiguation Router and Blackbox Test Suite Modular Decomposition (`tests/test_blackbox_intent_disambiguation.py` [457 lines], `intent.py` [371 lines]).
    - TASK-0095: Soundscape Blackbox Test Suite and Adaptive Mixer Modular Decomposition (`tests/test_blackbox_soundscape.py` [405 lines]).
    - TASK-0096: Stand-In Policy Guardrails and Hot-Swap Blackbox Test Suite Modular Decomposition (`tests/test_blackbox_stand_in_guardrails.py` [369 lines]).
    - TASK-0097: OpenPanel Analytics Blackbox Test Suite Modular Decomposition (`tests/test_blackbox_openpanel_analytics.py` [354 lines]).
  - Synchronized `ROADMAP.md`: marked Milestone 3 (AI DM & Ecosystem Expansion) as Complete with all epics delivered, and transitioned Milestone 4 (Broadcast Studio & Community Platform) to Current with TASK-0051 as foundational platform enabler.
  - Replenished ready buffer in `docs/project/backlog/refined/` to 10 items (JIT queue health) with rigorous blackbox TDD Definitions of Done, governing ADR citations, and INVEST alignment.
  - Re-indexed `docs/project/backlog/PRIORITY.md` maintaining strict priority hierarchy: Foundational Enablers → Milestone 4 Epics → Identified Invariant Refactorings → Future Milestones.
### Changed
- **Campaign Analytics Test Suite Modular Decomposition (`TASK-0115`, `ADR-0003`, `ADR-0005`, `ADR-0006`, `ADR-0011`)**:
  - Decomposed monolithic `tests/test_blackbox_campaign_analytics.py` into three focused blackbox test modules strictly under 200 lines each: `tests/test_blackbox_campaign_analytics_api.py` (REST endpoints, SpiceDB auth), `tests/test_blackbox_campaign_analytics_worker.py` (consumer group routing, event projections), and `tests/test_blackbox_campaign_analytics_storage.py` (spatial metrics, MVP ranking, chronicle timeline).
- **WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition (`TASK-0071`, `ADR-0001`, `ADR-0003`, `ADR-0005`, `ADR-0009`)**:
  - Decomposed monolithic test suite `tests/test_websocket_zanzibar_auth.py` into `tests/test_websocket_zanzibar_connect_auth.py` (connection admission, revocation) and `tests/test_websocket_zanzibar_mutators.py` (token moves, DM actions, event publishing).
  - Updated bridge module `tests/test_blackbox_websocket_zanzibar.py` and Diataxis guide `docs/how-to/define-spicedb-zanzibar-permissions.md`.
- **Missing Player AI Stand-In and Absentee Recap Test Suite Modular Decomposition (`TASK-0070`, `ADR-0002`, `ADR-0003`, `ADR-0006`, `ADR-0009`)**:
  - Decomposed `tests/test_stand_in_engine.py` into `tests/test_stand_in_tactics_unit.py` (stand-in penalties, personality traits) and `tests/test_blackbox_stand_in_service.py` (stand-in actions, event publishing, recap generation).
  - Updated Diataxis guide `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`.

- **OpenPanel Analytics Blackbox Test Suite Modular Decomposition (`TASK-0097`, `ADR-0003`, `ADR-0006`, `ADR-0009`)**:
  - Decomposed `tests/test_blackbox_openpanel_analytics.py` into `tests/test_blackbox_analytics_client.py` (anonymization, scrubbing, transport) and `tests/test_blackbox_analytics_worker.py` (Redis Streams consumer group, metric mapping, DLQ).
  - Updated Diataxis guide `docs/how-to/track-analytics-events.md`.
- **Battlemap Uploader Subviews and Grid Controller Modular Decomposition (`TASK-0078`, `ADR-0004`, `ADR-0009`, `ADR-0012`, `ADR-0013`)**:
  - Decomposed `services/board_state/ui/src/runefoble-map-uploader.ts` (formerly 315 lines) into focused subcomponents strictly adhering to Hard Invariant 6 (< 500 lines limit, all resulting modules < 130 lines):
    - `runefoble-map-dropzone.ts` (124 lines): Encapsulates drag-and-drop file listeners, file input handling, MIME validation, and Silo S3 multipart upload progress dispatch.
    - `runefoble-map-grid-config.ts` (123 lines): Encapsulates grid column/row sliders, shroud opacity sliders, cell-by-cell fog-of-war masking toggles, and reveal all/shroud all actions.
    - `runefoble-map-uploader.ts` (117 lines): Lean coordinator orchestrating subviews, managing high-level state, and dispatching the standard `map-uploaded` CustomEvent.
  - Added dedicated Storybook stories for decomposed subcomponents (`runefoble-map-dropzone.stories.ts`, `runefoble-map-grid-config.stories.ts`) with zero console errors.
  - Added blackbox frontdoor verification suite in `tests/test_microfrontends.py` verifying component line invariants, custom element registration, and Silo S3 asset upload frontdoors.
- **SpiceDB Live gRPC Client and Schema Bootstrapper Test Suite Modular Decomposition (`TASK-0081`, `ADR-0001`, `ADR-0005`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_spicedb_live.py` (306 lines) into two focused, single-responsibility test suites strictly adhering to Hard Invariant 6 (< 500 lines limit, all resulting files strictly < 180 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
    - `tests/test_spicedb_schema_bootstrap.py` (101 lines): Verifies `runefoble.zed` Zanzibar schema existence and definition syntax, error handling for empty schema files, schema bootstrapping against mock and live clients, and resilient in-memory fallback behavior when SpiceDB endpoints are unreachable.
    - `tests/test_blackbox_spicedb_live_grpc.py` (178 lines): Verifies live SpiceDB container gRPC connections, frontdoor campaign role assignment (`POST /api/v1/campaigns/{id}/roles`), fine-grained Zanzibar permission evaluations (`view`, `run_session`), and immediate permission revocation upon relationship tuple deletion.
  - Extracted shared SpiceDB container lifecycle and port allocation fixtures to `tests/helpers/spicedb.py` (76 lines) and registered the plugin globally in `tests/conftest.py`.
- **Gateway WebSocket Hub and Action Validator Modular Decomposition (`TASK-0080`, `ADR-0001`, `ADR-0005`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed monolithic `gateway/api/src/gateway_api/websocket.py` (351 lines) into modular single-responsibility components strictly complying with Hard Invariant 6 (< 500 lines limit, all resulting modules strictly < 150 lines):
    - `websocket_validator.py` (136 lines): Encapsulates `WebSocketActionValidator` evaluating fine-grained SpiceDB Zanzibar schema checks for connection admission, DM bypass privileges, token moves, character edits, and DM-only encounter mutations.
    - `websocket_manager.py` (51 lines): Encapsulates `CampaignConnectionManager` (with alias `CampaignWebSocketManager` and singleton `ws_campaign_manager`) tracking active campaign connection pools and broadcasting state frames.
    - `websocket_auth.py` (74 lines): Encapsulates credential extraction (`extract_token_from_websocket`, `extract_subject_id`) and handshake authentication (`authenticate_websocket`) validating Zitadel RS256 JWTs across query parameters, Bearer headers, and subprotocols.
    - `websocket_endpoint.py` (139 lines): Encapsulates `campaign_websocket_endpoint` handling the WebSocket lifecycle, Zanzibar admission verification, Redis event stream publishing, and disconnect handling.
    - `websocket.py` (50 lines): Acts as a backward-compatible facade re-exporting all validator, manager, auth, and endpoint symbols to ensure zero breaking changes across existing callers and tests.
  - Added comprehensive modular and frontdoor test coverage in `tests/test_websocket_modular_decomposition.py` verifying module line invariants (< 150 lines), re-export parity, direct policy validation, and WebSocket broadcasting.
  - Updated Diataxis reference documentation in `docs/reference/ports-and-endpoints.md` and explanation in `docs/explanation/realtime-voice-and-board-sync.md`.

- **Stand-In Policy Guardrails and Hot-Swap Blackbox Test Suite Modular Decomposition (`TASK-0096`, `ADR-0001`, `ADR-0002`, `ADR-0003`, `ADR-0009`)**:
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_stand_in_guardrails.py` (370 lines) into two focused, single-responsibility test suites strictly adhering to Hard Invariant 6 (< 500 lines limit, all files strictly < 190 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
    - `tests/test_blackbox_stand_in_policies.py` (189 lines): Verifies tactical guardrail configuration via `PUT/GET /api/v1/characters/{id}/guardrails`, SpiceDB Zanzibar authorization, `StandInPolicyUpdated` and `StandInStabilized` CloudEvent publications, The Watcher stand-in tactical decision graph evaluation under 'drunk' and 'foolishness' penalties, and zero-HP permadeath stabilization invariants.
    - `tests/test_blackbox_stand_in_takeover.py` (147 lines): Verifies mid-session hot-swap handoffs via `POST /api/v1/sessions/{id}/hot-swap`, active combat round and initiative continuity, SpiceDB Zanzibar object authorization, and `CharacterControlTransferred` CloudEvent emissions.
  - Updated Diataxis documentation in `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`.
- **Silo S3 Media Asset Bucket Storage and Battlemap Pipeline Test Suite Modular Decomposition (`TASK-0067`, `ADR-0003`, `ADR-0009`, `ADR-0013`)**:
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_silo_assets.py` (362 lines) into two specialized, single-responsibility test suites strictly adhering to Hard Invariant 6 (< 500 lines limit, all resulting files strictly < 220 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
    - `tests/test_blackbox_silo_asset_lifecycle.py` (202 lines): Verifies multipart/form-data and JSON base64 uploads for avatar images, tactical battlemaps, and audio soundscapes, direct binary streaming (`/stream`), attachment download headers (`/download`), MIME type validation, maximum payload limits (10MB), and deletion lifecycle with subsequent 404 responses.
    - `tests/test_blackbox_silo_asset_events.py` (143 lines): Verifies CloudEvents 1.0 schema compliance and EventRegistry registration for `AssetUploaded` and `AssetDeleted`, Redis Streams stream publishing (`runefoble.events.asset`), in-memory platform bus delivery, and Swagger UI / OpenAPI route declarations (`/openapi.json`).
  - Extracted shared test fixtures and constants to `tests/helpers/silo_fixtures.py` (39 lines) including `PNG_SAMPLE_BYTES`, `WAV_SAMPLE_BYTES`, and `clean_storage_and_bus` isolation fixture, registered via `tests/conftest.py`.

- **Intent Disambiguation Router and Blackbox Test Suite Modular Decomposition (`TASK-0094`, `ADR-0002`, `ADR-0003`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed `services/the_watcher/src/the_watcher/routers/intent.py` (371 lines) into modular sub-routers in `services/the_watcher/src/the_watcher/routers/intent/`:
    - `disambiguation.py` (195 lines): Ambiguity detection, clarification prompts, target candidate matching, and `/resolve` route.
    - `compound.py` (83 lines): Compound action combo decomposition, sequential execution, and rollback handling.
    - `speech.py` (137 lines): Single speech-to-intent parsing (`/transcribe-and-act` and `/intent`), domain event dispatch, and board token moves.
    - `__init__.py` (40 lines): Primary APIRouter facade re-exporting existing `/intent` routes with 100% backward compatibility.
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_intent_disambiguation.py` (458 lines) into partitioned test suites:
    - `tests/test_blackbox_intent_disambiguation_flow.py` (229 lines): Blackbox TDD coverage for multi-target disambiguation, ghost previews, player clarification, and sub-400ms SLA timing.
    - `tests/test_blackbox_intent_compound_combos.py` (200 lines): Blackbox TDD coverage for compound combo ordering, intermediate disambiguation, and partial failure rollbacks.
  - Enforced Hard Invariant 6 (< 500 lines limit, all router files strictly < 200 lines, all test files strictly < 250 lines).
  - Updated Diataxis documentation in `docs/how-to/decompose-microservice-routers.md` and `docs/how-to/resolve-conversational-disambiguation-and-combos.md`.

- **Project Visualizer Interactive Graph Zoom and Live Minimap Navigation (`tools/project_visualizer/`, `ADR-0003`, `ADR-0004`)**:
  - Implemented mouse-anchored focal zoom in `graph_camera.js`, keeping the world point under the cursor stationary during mouse wheel scrolling and double-click zoom.
  - Resolved minimap node synchronization: minimap nodes now dynamically update their `cx` and `cy` positions on every simulation tick, layout transformation, and tactile node drag.
  - Added real-time minimap camera navigation: clicking or dragging anywhere on the bird's-eye minimap smoothly repositions the viewport camera to that world coordinate.
  - Removed fixed `viewBox` distortion from the main graph SVG viewport, enabling pixel-perfect 1:1 canvas panning and tactile node dragging with grab offset preservation.
  - Added crisp `vector-effect: non-scaling-stroke` styling to minimap viewport framing rectangles and node dots.
  - Modularized client graph architecture by decomposing `graph.js` into `graph.js` (371 lines) and `graph_camera.js` (255 lines), strictly satisfying Hard Invariant 6 (< 500 lines per file).

- **Soundscape Blackbox Test Suite and Adaptive Mixer Modular Decomposition (`TASK-0095`, `ADR-0003`, `ADR-0007`, `ADR-0009`, `ADR-0013`)**:
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_soundscape.py` (406 lines) into two focused, single-responsibility test suites strictly adhering to Hard Invariant 6 (< 500 lines limit, all files strictly < 220 lines) and Hard Invariant 7 (Blackbox TDD with frontdoor setup):
    - `tests/test_blackbox_soundscape_transitions.py` (198 lines): Verifies stem mixer weights, background track crossfading, WebAudio -12dB voice ducking attenuation triggered by `PlayerSpokeEvent`, manual mood overrides, and `<runefoble-soundscape-controls>` microfrontend component and token invariants.
    - `tests/test_blackbox_soundscape_tension.py` (205 lines): Verifies encounter tension scoring heuristics across exploration and combat states, tactical foley cue triggers (`POST /api/v1/soundscape/cue`), autonomous Redis Streams reactivity to `CombatEncounterStarted` and `CombatRoundAdvanced`, and SpiceDB Zanzibar DM authorization enforcement.
  - Updated Diataxis documentation in `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`.
- **DM Co-Pilot Router and Blackbox Test Suite Modular Decomposition (`TASK-0093`, `ADR-0001`, `ADR-0002`, `ADR-0003`, `ADR-0009`, `ADR-0013`)**:
  - Decomposed `services/the_watcher/src/the_watcher/routers/copilot.py` (399 lines) into modular sub-routers in `services/the_watcher/src/the_watcher/routers/copilot/`:
    - `actions.py` (223 lines): Action proposal, pause window countdown, approve, modify, and veto override endpoints.
    - `whispers.py` (149 lines): Private narrative whisper creation, list, and unread status endpoints.
    - `__init__.py` (41 lines): Combined APIRouter re-exporting `/copilot` routes with 100% backward compatibility.
  - Decomposed monolithic blackbox test suite `tests/test_blackbox_dm_copilot.py` (474 lines) into partitioned test suites:
    - `tests/test_blackbox_dm_copilot_whispers.py` (209 lines): Blackbox TDD coverage for whisper generation, unread listing, and Zanzibar DM authorization.
    - `tests/test_blackbox_dm_copilot_actions.py` (238 lines): Blackbox TDD coverage for action proposal, pause window lifecycle, veto/approval CloudEvents, and parameter modification.
  - Enforced Hard Invariant 6 (< 500 lines limit, all modified and newly created files strictly < 250 lines).
  - Updated Diataxis documentation in `docs/how-to/decompose-microservice-routers.md` and `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`.

- **Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition (`TASK-0065`, `ADR-0002`, `ADR-0003`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed `services/voice_agent/src/voice_agent/dsp.py`, `services/voice_agent/src/voice_agent/main.py`, and `services/voice_agent/src/voice_agent/room.py` into single-responsibility modules strictly adhering to Hard Invariant 6 (< 500 lines per file, all modified and newly created modules strictly < 200 lines).
  - Created `services/voice_agent/src/voice_agent/phonetics.py` extracting regex-based phonetic transforms (`apply_slurred_speech`, sibilants slurring, vowel elongation, and hiccup insertions).
  - Created `services/voice_agent/src/voice_agent/audio_utils.py` isolating PCM array normalization and harmonic synthetic speech waveform generation.
  - Created `services/voice_agent/src/voice_agent/filters.py` isolating whisper, underwater, ethereal, and drunk audio DSP filter convolutions.
  - Refactored `services/voice_agent/src/voice_agent/dsp.py` into a thin pipeline orchestrator with full backward-compatible re-exports.
  - Decomposed room management into `room_aggregate.py` (event-sourced aggregate and peer state models) and `coordinator.py` (multi-session room orchestration and WebRTC telemetry), maintaining backward-compatible re-exports in `room.py`.
  - Extracted shared runtime state and event dispatchers into `dependencies.py` and schemas into `models.py`.
  - Created modular FastAPI sub-routers under `services/voice_agent/src/voice_agent/routers/` (`audio.py` for DSP conditioning and `synthesis.py` for STT/TTS synthesis).
  - Reduced `services/voice_agent/src/voice_agent/main.py` to a clean application bootstrap (< 125 lines).
  - Updated documentation in `docs/how-to/decompose-microservice-routers.md`.

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

- **Zitadel OIDC Token Verification and JWKS Blackbox Test Suite Modular Decomposition (`TASK-0079`, `ADR-0001`, `ADR-0005`, `ADR-0007`, `ADR-0009`)**:
  - Decomposed monolithic `tests/test_blackbox_zitadel_auth.py` (386 lines) into specialized, single-responsibility modules strictly adhering to Hard Invariant 6 (< 500 lines per file, all resulting files < 175 lines):
    - `tests/test_blackbox_zitadel_http_auth.py` (172 lines) covering HTTP Bearer token verification, RS256 signature verification, JWKS key rotation, token expiration, signature tampering, audience enforcement, and dev mode bypass.
    - `tests/test_blackbox_zitadel_websocket_auth.py` (156 lines) covering WebSocket query parameter authentication, Authorization header passing, `Sec-WebSocket-Protocol` subprotocol authentication, and RFC 6455 policy violation close frames (`code=4003`).
    - `tests/helpers/zitadel_auth.py` (115 lines) isolating shared RSA test key generation, JWK formatting, signed token generation, and the `auth_environment` fixture registered via `tests/conftest.py`.
  - Updated Diataxis guide `docs/how-to/authenticate-with-zitadel-oidc.md` detailing multi-channel token extraction and modular blackbox verification.

- **Backlog Engine Orchestrator and CI Watcher Modular Decomposition (`TASK-0091`, `ADR-0003`, `ADR-0009`)**:
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
- **PostgreSQL Event Store & Provisioning Test Suite Modular Decomposition (`TASK-0058`)**: Decomposed `tests/test_blackbox_postgres_event_store.py` into modular test suites (`tests/test_blackbox_postgres_provisioning.py` for multidb initialization and `tests/test_blackbox_postgres_event_store.py` for aggregate persistence roundtrips) and extracted shared helpers into `tests/helpers/postgres.py`, strictly enforcing Hard Invariant 6 with all files under 185 lines.
- **Campaign Lore Retrieval Modular Decomposition (`TASK-0089`)**: Decomposed monolithic `services/campaign_lore/src/campaign_lore/retrieval.py` into focused submodules `extraction.py` (NER regexes, entity typing heuristics, `WorldbuildingLlmProvider`), `scoring.py` (Okapi BM25 tokenization, term frequency weighting, cosine similarity, Reciprocal Rank Fusion), `models.py` (data models), and a lean coordinator `retrieval.py` (`LoreRetrievalEngine` / `HybridLoreEngine`) preserving Hard Invariant 6 (< 500 lines) and 100% backward compatibility.
- **Backlog Engine Test Suite Modular Decomposition (`TASK-0087`)**: Decomposed monolithic `tests/test_pr_conflict_detection.py` into three specialized suites (`tests/test_backlog_ci_watcher.py`, `tests/test_backlog_stale_recovery.py`, and `tests/test_backlog_pr_repair.py`), strictly enforcing Hard Invariant 6 (< 500 lines per file) with all suites well under 160 lines.
- **Documentation & Build Navigation**: Featured the Platform Showcase and Changelog in `zensical.toml` and root documentation landing page (`docs/index.md`), and enhanced `scripts/build_docs.py` to synchronize `CHANGELOG.md` to `docs/changelog.md` during documentation compilation.

### Fixed
- **Backlog Engine Missing & Concurrently Moved Task File Handling**:
  - Hardened `BacklogQueue` methods (`list_all_tasks`, `get_completed_task_ids`, `recover_stale_tasks`, `release_task`, and `complete_task`) against `FileNotFoundError` and `OSError` caused by race conditions during concurrent git pulls, task completions, and JIT backlog refinements.
  - Added cross-directory canonical task deduplication in `list_all_tasks` (`complete` > `refined` > `proposed`), preventing duplicate task processing across lifecycle directories.
  - Added unit test suite in `tests/test_backlog_queue.py` validating resilience against missing files, broken symlinks, and cross-folder transitions.
- **Project Visualizer Local Script Syntax & Favicon**: Fixed missing closing bracket in `agy_launcher.js` DOM listener causing `Uncaught SyntaxError` on local server, added automated Node.js syntax verification tests for all client scripts and bundles, and eliminated browser 404 console errors by handling `/favicon.ico` with 204 No Content and embedding an inline SVG dice icon.

---
## [0.2.0] - 2026-09-26

### Milestone 2: Live Collaborative Alpha
#### Added
- **Tactile Board Kinematics & Ghost Previews (`TASK-0084`, `PRD-0013`, `US-0043`)**: Drag-and-drop token physics with spring damping, velocity, 5ft step counting, and semi-transparent ghost preview trajectories for spoken movement commands validated against difficult terrain and hazards.
- **Streaming Whisper Speech-to-Intent Pipeline (`TASK-0039`, `TASK-0083`)**: Sub-500ms streaming Whisper audio transcription and intent classification with real-time voice intent extraction and multi-condition DSP voice filters.
- **Microfrontend Component Architecture (`ADR-0013`, `TASK-0024`, `TASK-0043`)**: Service bounded context component vendoring in `services/<bc>/ui/` with Shadow DOM encapsulation, runtime discovery via `/ui/manifest`, and decoupled App Shell.
- **Frontend Settings Modal & Theme Modes (`TASK-0073`, `TASK-0086`)**: Centralized settings modal with Dark, Light, and System preference mode orchestration and high-contrast Bauhaus modernist design tokens.
- **Live WebRTC Audio & S3 Asset Uploaders (`TASK-0030`, `TASK-0031`, `TASK-0033`)**: WebRTC voice room with audio waveform visualizer and Silo S3 battlemap uploader with shroud masking.
- **Enterprise Security & Event Store (`TASK-0032`, `TASK-0034`, `TASK-0035`, `TASK-0036`)**: Google Zanzibar authorization (SpiceDB), Zitadel OIDC authentication, PostgreSQL event store (`eventsource-py`), and Redis Streams bus (`TASK-0015`, `TASK-0042`).
- **Observability & Analytics (`TASK-0037`, `TASK-0038`, `TASK-0082`)**: OpenTelemetry distributed tracing with Collector/Loki/Grafana and privacy-preserving OpenPanel analytics SDK.
- **Autonomous Backlog Execution Engine (`TASK-0046`)**: Parallel worktree orchestrator (`scripts/run-backlog-engine.sh`), conflict detection, and interactive Project Visualizer web application.

#### Changed
- **Modular Router Refactoring (`TASK-0040`, `TASK-0041`, `TASK-0045`, `TASK-0085`)**: Decomposed monolithic FastAPI entrypoints into modular sub-routers across all bounded contexts and FastMCP tools into modular registries.

---
## [0.1.0] - 2026-09-20

### Milestone 1: Platform Foundation & Core Loop
#### Added
- **Monorepo Workspace Foundation (`TASK-0000`, `ADR-0003`)**: UV monorepo managing shared libraries (`runefoble_platform`, `runefoble_auth`, `runefoble_events`) and microservices.
- **Core Microservices & Tabletop Engine**: `the_watcher` (autonomous DM), `game_session` (lifecycle & dice), `board_state` (grid & tokens), `character_sheet` (stats), `voice_agent` (WebRTC audio DSP).
- **Unified API Gateway & FastMCP**: Gateway aggregating HTTP, WebSockets, Swagger UI, and FastMCP tabletop tools.
- **Infrastructure, Frontend & Diataxis Docs**: Kind Kubernetes cluster, Helm chart, Lit + Vite frontend with Storybook Bauhaus design system, and Diataxis documentation suite.

