# Platform Roadmap

## Milestone 1: Platform Foundation & Core Loop (Complete)
- [x] Monorepo UV workspace configuration
- [x] Core libraries (`runefoble_platform`, `runefoble_auth`, `runefoble_events`)
- [x] Initial microservices (`the_watcher`, `game_session`, `board_state`, `character_sheet`, `voice_agent`)
- [x] API Gateway and FastMCP server
- [x] Lit + Vite frontend with Storybook components
- [x] Kubernetes Kind cluster configuration and umbrella Helm chart
- [x] Swagger UI OpenAPI aggregation
- [x] Zanzibar authorization schema with SpiceDB

## Milestone 2: Live Collaborative Alpha (Complete)
### Foundational Platform Enablers
- [x] Redis Streams event streaming across distributed nodes (ADR-0006, TASK-0015)
- [x] SpiceDB production cluster syncing with Zitadel OIDC identities (ADR-0001, TASK-0032)
- [x] Zitadel production OIDC/JWKS token verification middleware (ADR-0005, TASK-0034)
- [x] Live SpiceDB gRPC client integration & schema migration bootstrapper (ADR-0001, TASK-0035)
- [x] PostgreSQL multi-database initialization & persistent event store connection (ADR-0011, TASK-0036)
- [x] OpenTelemetry distributed tracing, metrics & collector Helm integration (TASK-0037)
- [x] OpenPanel privacy-preserving analytics SDK & event pipeline (TASK-0038)

### Collaborative Feature Epics
- [x] WebRTC audio stream & real-time waveform visualizer microfrontend (ADR-0013, TASK-0030)
- [x] Silo S3 battlemap asset uploader & shroud masking microfrontend (ADR-0013, TASK-0031)
- [x] Live WebRTC bidirectional voice room with WebAudio processing (ADR-0002, TASK-0033)
- [x] Immersive frontend experience vision PRD (ADR-0004, TASK-0072)
- [x] Frontend settings modal and theme mode orchestration (ADR-0004, TASK-0073)
- [x] Dark/light mode color tokens and component contrast invariants (ADR-0012, TASK-0074)
- [x] Sub-500ms Whisper speech-to-intent pipeline (TASK-0039)
- [x] Tactile kinetic board interaction and spoken ghost previews (PRD-0013, US-0043, TASK-0084)

## Milestone 3: AI DM & Ecosystem Expansion (Complete)
### Foundational Platform Enablers
- [x] Campaign Lore Knowledge Base & redstring RAG Microservice (TASK-0047)
- [x] TTRPG Rules Compendium & Automated Encounter Builder (TASK-0048)

### Autonomous DM & Content Expansion Epics
- [x] Procedural battlemap and token generation saved to Silo S3 (TASK-0049)
- [x] Dynamic musical score & ambient foley driven by encounter tension (TASK-0050)
- [x] DM Co-Pilot Whispers & Veto Override Engine (TASK-0053)
- [x] Conversational Disambiguation & Compound Action Intents (TASK-0054)
- [x] Stand-In Policy Guardrails & Mid-Session Hot-Swap Takeover (TASK-0055)

## Milestone 4: Broadcast Studio & Community Platform (Complete)
### Foundational Platform Enablers
- [x] TypeScript Live Audience Studio & Spectator Interactivity (ADR-0001, ADR-0006, ADR-0007, TASK-0051)

### Broadcast & Interactivity Epics
- [x] Cinematic Director Auto-Camera & OBS Transparent Overlay (TASK-0056)
- [x] Campaign Telemetry, Analytics & Chronicle Archive (TASK-0052)
- [x] Campaign Telemetry Dashboard & Chronicle Timeline Microfrontend (PRD-0012, US-0040, US-0054, TASK-0110)
- [x] Universal VTT Importer & Dynamic MCP Tool Registry (TASK-0057)

## Milestone 5: Collaborative Creation, Downtime & Tactile Immersion (Complete)
### Downtime, Social Minigames & Base Building
- [x] Downtime Activities, Alchemical Crafting & Party Stronghold Engine (PRD-0014, US-0044, TASK-0100)
- [x] Interactive Tavern Minigames & Personality-Driven Merchant Haggling (PRD-0014, US-0047, TASK-0103)
- [x] Character Sheet UI Inventory Grid & Condition Indicators (PRD-0006, US-0015, US-0051, TASK-0107)

### Tactile Artifacts, Living Codex & Hybrid Maker
- [x] Generative Diegetic Handouts, Wax Seals & 3D Relic Inspector (PRD-0015, US-0045, TASK-0101)
- [x] Printable Tabletop Forge: Grid-Calibrated PDFs, Standees & 3D STL Tokens (PRD-0015, US-0049, TASK-0105)
- [x] Collaborative Campaign World Atlas & Living Party Codex (PRD-0015, US-0050, TASK-0106)
- [x] Rules Compendium Search & Encounter Builder Microfrontend (PRD-0008, US-0037, US-0052, TASK-0108)

### Expressive Performance, Audio Leitmotifs & Particle VFX
- [x] Personal Character Leitmotifs & Adaptive Musical Signatures (PRD-0016, US-0046, TASK-0102)
- [x] Multi-Modal Kinetic Spell VFX & WebGL Particle Magic (PRD-0016, US-0048, TASK-0104)
- [x] Generative Wardrobe, Emotion & State Portrait Gallery (PRD-0016, US-0055, TASK-0124)
- [x] Radial Token Action Menu & Rotatable AoE Spell Templates (PRD-0013, US-0056, TASK-0125)
- [x] Dynamic Soundscape Mixing Panel & Foley Soundboard Microfrontend (PRD-0010, US-0039, US-0053, TASK-0109)

## Milestone 6: Intelligent Living Worlds & Spatial Multi-Party Universes (Complete)
- [x] Autonomous NPC Faction Agendas & Background Simulation Engine (`FEAT-WAT-07`, US-0057, TASK-0126)
- [x] Multi-Party West Marches Shared Persistent World State & Cross-Campaign Trade (US-0058, TASK-0127)
- [x] Spatial Companion Mobile App, Haptic Secret Pings & WebRTC Gateway (US-0059, TASK-0128)
- [x] Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts (US-0058, TASK-0129)
- [x] Spatial Companion Mobile WebRTC Audio & Haptic Controller Microfrontend (US-0059, TASK-0134)
- [x] West Marches Shared World Atlas Pins & Communal Stronghold Dashboard Microfrontend (US-0050, US-0058, TASK-0135)
- [x] Cross-Campaign Caravan Trading & Frontier Bounty Board Microfrontend (US-0058, TASK-0136)
- [x] Autonomous NPC Faction Agendas Radar & Intelligence Bulletin Microfrontend (US-0057, TASK-0137)

## Milestone 7: Neural Audio Duplex & Tangible 3D Tabletop (Complete)
### Foundational Platform & Physics Enablers
- [x] Zero-Latency Neural Voice Duplex & Speech Interruption Handling (`FEAT-VOX-06`, US-0060, TASK-0141)
- [x] Tabletop 3D Physics Engine & Mesh Collision Integration (`FEAT-BRD-06`, US-0061, TASK-0150)

### Interactive Audio & 3D Tabletop Epics
- [x] 3D Miniature Tokens & WebGL Tabletop Physics (`FEAT-BRD-06`, US-0061, TASK-0142)
- [x] Voice Duplex Audio Settings & Real-Time Barge-In Visualizer Microfrontend (`FEAT-VOX-06`, US-0060, TASK-0149)

## Milestone 8: Reactive Tactical Environments & In-World DM Tools (Complete)
### Foundational Platform & Audio Enablers
- [x] Spoken Reaction Interrupts & Ready-Action Combat Triggers (`FEAT-WAT-08`, US-0023, PRD-0001, TASK-0155)
- [x] Secret DM Spatial Traps, Map Switching & Hidden Cell Triggers (`FEAT-BRD-07`, US-0018, PRD-0007, TASK-0156)
- [x] DM Live Vocal Modulator & Real-Time NPC Formant DSP Engine (`FEAT-VOX-07`, US-0020, PRD-0004, TASK-0157)
- [x] GameSession Aggregate and Reaction Handlers Modular Decomposition (TASK-0175)

### Tactical Reactions & DM Tooling Epics
- [x] Reactive Combat Reactions & Interrupt Prompt Microfrontend (`FEAT-WAT-08`, US-0023, PRD-0001, TASK-0158)
- [x] DM Hidden Layers & Multi-Map Switcher Microfrontend (`FEAT-BRD-07`, US-0018, PRD-0007, TASK-0159)
- [x] DM Vocal Modulator Controls & Preset Selector Microfrontend (`FEAT-VOX-07`, US-0020, PRD-0004, TASK-0160)

## Milestone 10: Complete Frontend Application Experience, User Identity & Campaign Orchestration (Active / Immediate Priority)
### Core Identity, Gateway & Shell Routing Enablers
- [x] Frontend SPA Client Router and Navigation Chrome (`FEAT-UI-11`, US-0066, PRD-0023, TASK-0206)
- [x] Zitadel Auth Client and Login Modal Component (`FEAT-UI-07`, `FEAT-SEC-02`, US-0062, PRD-0023, TASK-0207)
- [x] Gateway Campaign Lifecycle and Membership API (`FEAT-UI-08`, `FEAT-SEC-01`, US-0063, PRD-0023, TASK-0208)

### Campaign Hub, Character Roster & Pre-Game Lobby Epics
- [x] Campaign Dashboard and Creation Microfrontend (`FEAT-UI-08`, US-0063, PRD-0023, TASK-0209)
- [x] Campaign Members and Zanzibar Role Manager UI (`FEAT-UI-08`, `FEAT-SEC-01`, US-0063, PRD-0023, TASK-0210)
- [x] Character Roster and Party Assignment Microfrontend (`FEAT-UI-09`, US-0064, PRD-0023, TASK-0211)
- [x] Game Session Lobby and Readiness Microfrontend (`FEAT-UI-10`, US-0065, PRD-0023, TASK-0212)
- [x] App Shell View Orchestration and Session Transition (`FEAT-UI-11`, US-0065, US-0066, PRD-0023, TASK-0213)

### Frontdoor Blackbox Verification Suites
- [x] Frontend Routing and Auth Blackbox Test Suite (US-0062, US-0066, PRD-0023, TASK-0214)
- [x] Campaign Management and Lobby Blackbox Test Suite (US-0063, US-0064, US-0065, PRD-0023, TASK-0215)

### Extended Campaign Hub & Character Management Enablers (Phase 2)
- [x] Gateway Campaign Sessions API and Persistence (`FEAT-UI-08`, US-0063, US-0067, PRD-0023, TASK-0246)
- [x] Frontend Vite API Proxy and Dynamic Route Title Resolver (`FEAT-UI-11`, US-0066, PRD-0023, TASK-0247)
- [x] Gateway Character Management Router and Zanzibar Authorization (`FEAT-UI-09`, US-0064, PRD-0023, TASK-0252)
- [x] Character Aggregate Campaign Assignment and Core Attributes Extension (`FEAT-UI-09`, US-0064, PRD-0006, TASK-0253)

### Extended Campaign Hub & Character Management Epics (Phase 2)
- [x] Campaign Detail Hero Header and Metadata Component (`FEAT-UI-08`, US-0067, PRD-0023, TASK-0248)
- [x] Session Scheduling and Staging Lobby Creation Modal (`FEAT-UI-10`, US-0065, US-0067, PRD-0023, TASK-0249)
- [x] Unified Campaign Detail View Orchestration and Tabbed Navigation (`FEAT-UI-08`, US-0067, PRD-0023, TASK-0250)
- [x] Frontend Character Roster Event Binding and Data Mutations (`FEAT-UI-09`, US-0064, US-0069, PRD-0023, TASK-0254)
- [x] Character Sheet Route and Inspector Subview Orchestration (`FEAT-UI-09`, US-0069, PRD-0023, TASK-0255)
- [x] Dynamic Character Binding in Pre-Game Lobby and Active VTT (`FEAT-UI-10`, US-0065, US-0069, PRD-0023, TASK-0256)
- [x] Profile Settings View and Campaign Creation Idempotency (`FEAT-UI-08`, US-0063, US-0068, PRD-0023, TASK-0257)

### Phase 2 Verification Suites
- [x] App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite (US-0065, US-0066, PRD-0023, TASK-0251)
- [ ] Character Management and Tabletop Sync Blackbox Test Suite (US-0064, US-0069, PRD-0023, TASK-0258)

## Milestone 11: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames
### Foundational Aggregates, Social Graphs & Civic Enablers
- [x] Settlement Haven Builder and Establishment Aggregate (`FEAT-SET-01`, `FEAT-SET-02`, US-0072, PRD-0024, TASK-0259)
- [ ] Assignable NPC Worker and Social Relationship Graph (`FEAT-SET-02`, US-0073, PRD-0024, TASK-0260)

### Mobile Minigames, Haggling & Notice Board Epics
- [ ] Mobile-First Touch-Optimized Tavern & Casino Minigames (`FEAT-SET-03`, US-0074, PRD-0024, TASK-0261)
- [ ] Interactive Merchant Haggling Engine with DM Controls (`FEAT-SET-04`, US-0075, PRD-0024, TASK-0262)
- [ ] Town Bulletin Board Civic Notices and Bounty Board (`FEAT-SET-05`, US-0076, PRD-0024, TASK-0263)

### Settlement & Minigames Blackbox Verification
- [ ] Settlement Builder and Minigames Blackbox Test Suite (US-0072, US-0073, US-0074, US-0075, US-0076, PRD-0024, TASK-0264)

## Milestone 9: Persona Immersion & Community Ecosystem
### Living Worlds, Mobile & Voice Enablers

- [x] NPC Faction Resource Operations and Bribery Mechanics Aggregate (`FEAT-WAT-07`, US-0057, PRD-0017, TASK-0161)
- [x] Faction Turf War and Regional Unrest Event Pipeline (`FEAT-WAT-07`, US-0057, US-0019, PRD-0017, TASK-0162)
- [x] Cross-Campaign Settlement and Haven Registry (`FEAT-LRE-04`, US-0058, PRD-0018, TASK-0164)
- [x] Frontier Mercenary Contract and Bounty Board Router (`FEAT-DWN-04`, US-0058, PRD-0018, TASK-0165)
- [x] Mobile Low-Bandwidth Opus Adaptive Stream Adapter (`FEAT-VOX-01`, US-0059, PRD-0019, TASK-0166)
- [x] Neural Speech Barge-In and Soft Crossfade Audio Filter (`FEAT-VOX-06`, US-0060, PRD-0020, TASK-0168)
- [x] Hardware Acoustic Echo Cancellation and ERLE Validation (`FEAT-VOX-06`, US-0060, PRD-0020, TASK-0169)
- [x] Dynamic FastMCP Tool Hot-Reloading Registry (`FEAT-DEV-01`, US-0008, US-0035, PRD-0022, TASK-0172)
- [x] Universal VTT Door and Dynamic Lighting Parser (`FEAT-BRD-05`, US-0033, PRD-0022, TASK-0173)

### Multi-Party, Physics & Extensible UI Epics
- [x] Faction Espionage and Alert Feeds Microfrontend (`FEAT-WAT-07`, US-0057, PRD-0017, TASK-0163)
- [x] Absentee Mobile Directive and Remote Voting Microfrontend (`FEAT-WAT-05`, US-0059, US-0027, PRD-0019, TASK-0167)
- [x] Kinetic 3D Dice Physics and Tray Audio Integration (`FEAT-BRD-06`, US-0061, PRD-0021, TASK-0170)
- [x] Miniature Knockback Impulse and Elevation Physics (`FEAT-BRD-06`, US-0061, PRD-0021, TASK-0171)
- [x] Community Plugin UI Extension Slots Microfrontend (`FEAT-DEV-01`, US-0035, PRD-0022, TASK-0174)

### Continuous Architecture & Modular Refactorings
- [x] West Marches UI Blackbox Test Suite Modular Decomposition (TASK-0176)
- [x] Runefoble Events Aggregator Modular Decomposition (TASK-0177)
- [x] GameSession Models Modular Decomposition (TASK-0178)
- [x] Rules Compendium Homebrew Subview Modular Decomposition (TASK-0179)
- [x] Board State Stories Modular Decomposition (TASK-0180)
- [x] Soundscape Event Handlers and Dependencies Modular Decomposition (TASK-0181)
- [x] Watcher Domain Events Modular Decomposition (TASK-0182)
- [x] Faction Resources Blackbox Test Suite Modular Decomposition (TASK-0183)
- [x] Campfire Crafting Blackbox Test Suite Modular Decomposition (TASK-0184)
- [x] Rules Compendium Styles Modular Decomposition (TASK-0185)
- [x] Caravan Aggregate and Contract Models Modular Decomposition (TASK-0186)
- [x] Campaign Atlas Blackbox Test Suite Modular Decomposition (TASK-0187)
- [x] Board State Previews Router Modular Decomposition (TASK-0188)
- [x] Character Sheet UI Templates Modular Decomposition (TASK-0189)
- [x] Cinematic Director Blackbox Test Suite Modular Decomposition (TASK-0190)
- [x] Kinetic Spell VFX Blackbox Test Suite Modular Decomposition (TASK-0191)
- [x] Board Templates Rendering and Subviews Modular Decomposition (TASK-0192)
- [x] Universal VTT Importer and Dynamic MCP Test Suite Modular Decomposition (TASK-0193)
- [x] Combat Heatmap Canvas Rendering and Subviews Modular Decomposition (TASK-0194)
- [x] Faction Radar SVG and Drawer Subviews Modular Decomposition (TASK-0195)
- [x] Campaign Atlas Layers and Pins Subviews Modular Decomposition (TASK-0196)
- [x] Asset Forge Raster Generator Modular Decomposition (TASK-0197)
- [x] Campaign Lore Codex Router Modular Decomposition (TASK-0198)
- [x] Campfire Crafting Subviews Modular Decomposition (TASK-0199)
- [x] Campaign Analytics Stories Fixtures Modular Decomposition (TASK-0200)
- [x] Board State Radial Menu Glyphs and Styles Modular Decomposition (TASK-0201)
- [x] Backlog Queue Parser and Serializer Modular Decomposition (TASK-0202)
- [x] Stand-In Guardrails Microfrontend Styles and Controls Modular Decomposition (TASK-0203)
- [x] Character Sheet Component Action Handlers and State Modular Decomposition (TASK-0204)
- [x] West Marches Aggregate Discovery and Territory Handlers Modular Decomposition (TASK-0205)
- [x] Faction Turf War Test Suite Modular Decomposition (TASK-0216)
- [x] Project Visualizer Graph Rendering Modular Decomposition (TASK-0217)
- [x] Project Visualizer AGY Test Suite Modular Decomposition (TASK-0218)
- [x] Project Visualizer Drawer Subviews Modular Decomposition (TASK-0219)
- [x] Campaign Members Styles Modular Decomposition (TASK-0220)
- [x] Gateway Campaign Store Modular Decomposition (TASK-0221)
- [ ] Character Roster Styles Modular Decomposition (TASK-0222)
- [x] Session Lobby Styles Modular Decomposition (TASK-0223)
- [ ] Project Visualizer AGY Launcher Modular Decomposition (TASK-0224)
- [ ] Campaign and Lobby Blackbox Test Suite Modular Decomposition (TASK-0225)
- [ ] Campaign Dashboard Styles Modular Decomposition (TASK-0226)
- [ ] Project Visualizer Graph Builder Modular Decomposition (TASK-0227)
- [ ] PRD Pipeline Manager Modular Decomposition (TASK-0228)
- [ ] Character Sheet Models Modular Decomposition (TASK-0229)
- [ ] Soundscape Aggregate Handlers Modular Decomposition (TASK-0230)
- [ ] Board Domain Events Modular Decomposition (TASK-0231)
- [x] Rules Compendium UI Blackbox Test Suite Modular Decomposition (TASK-0232)
- [ ] Character Leitmotif Generator Modular Decomposition (TASK-0233)
- [ ] Campfire Crafting Styles Modular Decomposition (TASK-0234)
- [ ] Project Visualizer Gantt Chart Modular Decomposition (TASK-0235)
- [x] Character Sheet UI Blackbox Test Suite Modular Decomposition (TASK-0236)
- [ ] Caravan Board UI Blackbox Test Suite Modular Decomposition (TASK-0237)
- [ ] GameSession Models Test Suite Modular Decomposition (TASK-0238)
- [ ] Asset Forge Print Forge Router Modular Decomposition (TASK-0239)
- [ ] Faction Simulation Engine Modular Decomposition (TASK-0240)
- [x] Gateway Auth Router Modular Decomposition (TASK-0241)
- [x] Platform Email Client Modular Decomposition (TASK-0242)
- [ ] Email Signup Mailpit Blackbox Test Suite Decomposition (TASK-0243)
- [ ] Rules Compendium Hybrid Retrieval Modular Decomposition (TASK-0244)
- [x] Campaign Lore Dependencies and Permissions Modular Decomposition (TASK-0245)
- [ ] Gateway Campaign Store Test Suite Modular Decomposition (TASK-0265)
- [ ] Vocal Modulator Blackbox Test Suite Modular Decomposition (TASK-0266)
- [ ] Rules Compendium Encounter Builder Subviews Modular Decomposition (TASK-0267)
- [ ] Radial Menu and AoE Templates Test Suite Modular Decomposition (TASK-0268)
- [x] Campaign Header Styles Modular Decomposition (TASK-0269)
- [ ] Session Modal Component and Form Styles Modular Decomposition (TASK-0270)
- [x] Frontend App Data Service Fixtures and Client Modular Decomposition (TASK-0271)
- [ ] Settlement Haven Aggregate Blackbox Test Suite Modular Decomposition (TASK-0272)
- [ ] Settlement Aggregate and Bulletin Handlers Modular Decomposition (TASK-0273)
- [ ] Settlement Bulletin Board Styles Modular Decomposition (TASK-0274)
- [ ] NPC Worker Engine Blackbox Test Suite Modular Decomposition (TASK-0275)
- [ ] Settlement Bulletin Board Blackbox Test Suite Modular Decomposition (TASK-0276)
