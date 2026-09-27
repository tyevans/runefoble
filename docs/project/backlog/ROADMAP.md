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

## Milestone 9: Persona Immersion & Community Ecosystem (Current)
### Living Worlds, Mobile & Voice Enablers
- [x] NPC Faction Resource Operations and Bribery Mechanics Aggregate (`FEAT-WAT-07`, US-0057, PRD-0017, TASK-0161)
- [ ] Faction Turf War and Regional Unrest Event Pipeline (`FEAT-WAT-07`, US-0057, US-0019, PRD-0017, TASK-0162)
- [ ] Cross-Campaign Settlement and Haven Registry (`FEAT-LRE-04`, US-0058, PRD-0018, TASK-0164)
- [ ] Frontier Mercenary Contract and Bounty Board Router (`FEAT-DWN-04`, US-0058, PRD-0018, TASK-0165)
- [ ] Mobile Low-Bandwidth Opus Adaptive Stream Adapter (`FEAT-VOX-01`, US-0059, PRD-0019, TASK-0166)
- [ ] Neural Speech Barge-In and Soft Crossfade Audio Filter (`FEAT-VOX-06`, US-0060, PRD-0020, TASK-0168)
- [ ] Hardware Acoustic Echo Cancellation and ERLE Validation (`FEAT-VOX-06`, US-0060, PRD-0020, TASK-0169)
- [ ] Dynamic FastMCP Tool Hot-Reloading Registry (`FEAT-DEV-01`, US-0008, US-0035, PRD-0022, TASK-0172)
- [ ] Universal VTT Door and Dynamic Lighting Parser (`FEAT-BRD-05`, US-0033, PRD-0022, TASK-0173)

### Multi-Party, Physics & Extensible UI Epics
- [ ] Faction Espionage and Alert Feeds Microfrontend (`FEAT-WAT-07`, US-0057, PRD-0017, TASK-0163)
- [ ] Absentee Mobile Directive and Remote Voting Microfrontend (`FEAT-WAT-05`, US-0059, US-0027, PRD-0019, TASK-0167)
- [ ] Kinetic 3D Dice Physics and Tray Audio Integration (`FEAT-BRD-06`, US-0061, PRD-0021, TASK-0170)
- [ ] Miniature Knockback Impulse and Elevation Physics (`FEAT-BRD-06`, US-0061, PRD-0021, TASK-0171)
- [ ] Community Plugin UI Extension Slots Microfrontend (`FEAT-DEV-01`, US-0035, PRD-0022, TASK-0174)

### Continuous Architecture & Modular Refactorings
- [ ] West Marches UI Blackbox Test Suite Modular Decomposition (TASK-0176)
- [ ] Runefoble Events Aggregator Modular Decomposition (TASK-0177)
- [ ] GameSession Models Modular Decomposition (TASK-0178)



