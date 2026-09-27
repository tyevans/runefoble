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

## Milestone 5: Collaborative Creation, Downtime & Tactile Immersion (Current)
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
- [ ] Personal Character Leitmotifs & Adaptive Musical Signatures (PRD-0016, US-0046, TASK-0102)
- [ ] Multi-Modal Kinetic Spell VFX & WebGL Particle Magic (PRD-0016, US-0048, TASK-0104)
- [ ] Generative Wardrobe, Emotion & State Portrait Gallery (PRD-0016, US-0055, TASK-0124)
- [ ] Radial Token Action Menu & Rotatable AoE Spell Templates (PRD-0013, US-0056, TASK-0125)
- [x] Dynamic Soundscape Mixing Panel & Foley Soundboard Microfrontend (PRD-0010, US-0039, US-0053, TASK-0109)

## Milestone 6: Intelligent Living Worlds & Spatial Multi-Party Universes
- [ ] Autonomous NPC Faction Agendas & Background Simulation Engine (`FEAT-WAT-07`, US-0057, TASK-0126)
- [ ] Multi-Party West Marches Shared Persistent World State & Cross-Campaign Trade (US-0058, TASK-0127)
- [ ] Spatial Companion Mobile App, Haptic Secret Pings & WebRTC Gateway (US-0059, TASK-0128)

