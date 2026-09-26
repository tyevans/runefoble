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

## Milestone 2: Live Collaborative Alpha (Current)
### Foundational Platform Enablers
- [x] Redis Streams event streaming across distributed nodes (ADR-0006, TASK-0015)
- [x] SpiceDB production cluster syncing with Zitadel OIDC identities (ADR-0001, TASK-0032)
- [ ] Zitadel production OIDC/JWKS token verification middleware (ADR-0005, TASK-0034)
- [ ] Live SpiceDB gRPC client integration & schema migration bootstrapper (ADR-0001, TASK-0035)
- [ ] PostgreSQL multi-database initialization & persistent event store connection (ADR-0011, TASK-0036)
- [ ] OpenTelemetry distributed tracing, metrics & collector Helm integration (TASK-0037)
- [ ] OpenPanel privacy-preserving analytics SDK & event pipeline (TASK-0038)

### Collaborative Feature Epics
- [ ] WebRTC audio stream & real-time waveform visualizer microfrontend (ADR-0013, TASK-0030)
- [ ] Silo S3 battlemap asset uploader & shroud masking microfrontend (ADR-0013, TASK-0031)
- [ ] Live WebRTC bidirectional voice room with WebAudio processing (ADR-0002, TASK-0033)
- [ ] Sub-500ms Whisper speech-to-intent pipeline (TASK-0039)

## Milestone 3: AI DM & Ecosystem Expansion
- [ ] Procedural battlemap generation saved to Silo S3
- [ ] Dynamic musical score & ambient foley driven by encounter tension
- [ ] Third-party MCP agent plugins (e.g. D&D Beyond / Pathfinder 2e rule compendiums)
