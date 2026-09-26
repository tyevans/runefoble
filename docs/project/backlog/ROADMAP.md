# Platform Roadmap

## Milestone 1: Platform Foundation & Core Loop (Current)
- [x] Monorepo UV workspace configuration
- [x] Core libraries (`runefoble_platform`, `runefoble_auth`, `runefoble_events`)
- [x] Initial microservices (`the_watcher`, `game_session`, `board_state`, `character_sheet`, `voice_agent`)
- [x] API Gateway and FastMCP server
- [x] Lit + Vite frontend with Storybook components
- [x] Kubernetes Kind cluster configuration and umbrella Helm chart
- [x] Swagger UI OpenAPI aggregation
- [x] Zanzibar authorization schema with SpiceDB

## Milestone 2: Live Collaborative Alpha
- [x] Redis Streams event streaming across distributed nodes (ADR-0006, TASK-0015)
- [ ] Zitadel production OIDC/JWKS token verification middleware (TASK-0030, Enabler)
- [ ] Live SpiceDB gRPC client integration & schema migration bootstrapper (TASK-0031, Enabler)
- [x] SpiceDB production cluster syncing with Zitadel OIDC identities (TASK-0024, Enabler)
- [ ] PostgreSQL multi-database initialization & persistent event store connection (TASK-0033, Enabler)
- [ ] OpenTelemetry distributed tracing, metrics & collector Helm integration (TASK-0029, Enabler)
- [ ] OpenPanel privacy-preserving analytics SDK & event pipeline (TASK-0032, Enabler)
- [ ] Live WebRTC bidirectional voice room with WebAudio processing (TASK-0025)
- [ ] Sub-500ms Whisper speech-to-intent pipeline (TASK-0027)

## Milestone 3: AI DM & Ecosystem Expansion
- [ ] Procedural battlemap generation saved to Silo S3
- [ ] Dynamic musical score & ambient foley driven by encounter tension
- [ ] Third-party MCP agent plugins (e.g. D&D Beyond / Pathfinder 2e rule compendiums)
