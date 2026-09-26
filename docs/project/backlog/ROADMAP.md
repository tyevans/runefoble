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
- [ ] Live WebRTC bidirectional voice room with WebAudio processing
- [ ] Sub-500ms Whisper speech-to-intent pipeline
- [ ] NATS JetStream event streaming across distributed nodes
- [ ] SpiceDB production cluster syncing with Zitadel OIDC identities

## Milestone 3: AI DM & Ecosystem Expansion
- [ ] Procedural battlemap generation saved to Silo S3
- [ ] Dynamic musical score & ambient foley driven by encounter tension
- [ ] Third-party MCP agent plugins (e.g. D&D Beyond / Pathfinder 2e rule compendiums)
