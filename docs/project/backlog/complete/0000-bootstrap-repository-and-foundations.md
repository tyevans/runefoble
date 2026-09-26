# TASK-0000: Bootstrap Repository and Platform Foundations

## Description
Establish the foundational monorepo structure, core Python libraries, cohesive initial microservices, Lit + Vite + Storybook frontend, Kubernetes deployment manifests (Kind + Helm + Traefik), and Diataxis/Cachette documentation architecture.

## Governing Documents
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005
- PRDs: PRD-0001, PRD-0002
- User Stories: US-0001, US-0002, US-0003, US-0004

## Deliverables Completed
- [x] UV monorepo workspace containing `libs/`, `services/`, and `gateway/`
- [x] `libs/runefoble_platform`: Platform configuration, base models, errors, event bus
- [x] `libs/runefoble_auth`: Zitadel JWT decoding and SpiceDB Zanzibar client with `runefoble.zed` schema
- [x] `libs/runefoble_events`: CloudEvents-compatible domain events
- [x] `services/the_watcher`: Speech-to-intent, autonomous DM narration, and missing player AI stand-in
- [x] `services/game_session`: Session state, turns, and participant presence
- [x] `services/board_state`: Tactical map, token coordinates, and movement validation
- [x] `services/character_sheet`: Character sheets, stats, and session miss penalties
- [x] `services/voice_agent`: STT/TTS pipeline and voice persona synthesis
- [x] `gateway/api`: API gateway with WebSocket real-time fanout and OpenAPI docs
- [x] `gateway/mcp`: FastMCP server exposing RPG tools and board controls to AI agents
- [x] `frontend/`: Lit web components, Vite app, and Storybook component studio
- [x] `deployments/helm/runefoble`: Umbrella Helm chart including Traefik, Postgres, Silo, Zitadel, SpiceDB, OpenPanel, Loki/Grafana, and Swagger UI aggregator
- [x] `deployments/kind/cluster-config.yaml`: Kind cluster config with ingress port mappings
- [x] `Makefile`: Developer interface for building, testing, linting, and running clusters
