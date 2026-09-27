# Runefoble

Runefoble is an imaginative gaming platform for storytellers of all ages (a collaborative tabletop roleplaying service).
Using advanced AI (LLMs and machine learning models), Runefoble delivers the highest quality, lowest friction collaborative storytelling experience in the world.

Speak and the board obeys: natural speech is parsed into game actions and applied directly to the game state, while The Watcher and the Game Master explore the narrative consequences. Real-time board animations, collaborative chat, voice streaming, autonomous DMing, and missing player AI stand-ins (with humorous DM penalties like "drunk" and "foolishness") are core capabilities.

## Status

The platform foundation is established.[^1] The monorepo UV workspace holds core libraries, initial microservices, gateways, a Lit + Vite frontend with Storybook components, and a Kubernetes-first infrastructure based on Helm and Kind.[^2]

Read the registers before you write code. Do not invent structures that contradict existing records.[^3]

## Target Platform & Infrastructure

Development runs locally in **Kind (Kubernetes IN Docker)** with Traefik ingress and is deployed via **Helm**.[^4]
- **Authentication & Identity**: Self-hosted **Zitadel** container (OIDC/JWT).[^5]
- **Fine-Grained Authorization**: Self-hosted **SpiceDB** container enforcing Zanzibar object-level permissions.[^6]
- **Database**: **PostgreSQL**.[^7]
- **Object Storage**: **Silo** (S3-compatible MinIO fork).[^8]
- **Analytics**: Self-hosted **OpenPanel** container.[^9]
- **Observability**: **OpenTelemetry** traces and metrics sent to **Grafana** and **Loki**.[^10]
- **Documentation Aggregator**: **Swagger UI** aggregating OpenAPI specs across all services into a single interface.[^11]

## Hard Invariants

These rules are structural. Do not violate them for convenience.

1. **Object-level authorization runs through SpiceDB Zanzibar schema.** Never hardcode role checks (e.g. `user.role == 'admin'`) in business logic. Check permissions against `libs/runefoble_auth/schema/runefoble.zed`.[^6]
2. **All domain state transitions and events are powered by eventsource-py.** Domain events inherit from `DomainEvent` (via `BaseRunefobleEvent` in `libs/runefoble_events`) and are registered with `@register_event`. Domain state changes flow strictly through `DeclarativeAggregate` subclasses with `@handles` methods and are saved/loaded via `AggregateRepository`.[^24]
3. **Frontend microfrontends are built and tested in Storybook first.** Build UI elements as Lit Web Components within their owning service bounded context (`services/<bc>/ui/src/`) and verify them in Storybook before composition into the lightweight `frontend/` App Shell.[^13][^25]
4. **All Python packages are managed through the root UV workspace.** Do not use pip, poetry, or virtualenvs directly. Run commands through `uv` or the developer `Makefile`.[^14]
5. **Services publish OpenAPI specs to the Swagger UI hub.** Every new HTTP service must expose `/openapi.json` and register its URL in `deployments/helm/runefoble/values.yaml`.[^11]
6. **File length limit (<500 lines).** Source files over ~500 lines are rarely justified. Whenever editing or committing code, inspect file lengths and decompose large files into focused, single-responsibility modules.
7. **Blackbox TDD with frontdoor setup.** All feature development must be driven by blackbox tests interacting strictly through public frontdoors (e.g. public HTTP routes, WebSockets, or published standard domain events) rather than reaching into private internals or backdoor state manipulation. Test setup must be performed through the frontdoor interfaces, and assertions must verify observable outputs, public query projections, or emitted standard events.

## Design Principles

- **Speak and the board obeys.** Spoken commands must be parsed into board mutations within 500ms without blocking audio pipelines.[^15]
- **The Watcher is an assistant, never a dictator.** The AI DM proposes actions and provides atmosphere, but players and human DMs always retain veto and override authority.[^16]
- **A missing player never cancels game night.** When a player is absent, an AI stand-in mimics their character traits, accepting playful session miss penalties ("drunk", "foolishness") inflicted by the DM.[^17]
- **Python is for services and orchestration; Web Components are for presentation.** Keep presentation logic isolated in Lit components with Shadow DOM encapsulation.[^13]

## Product & User Stories Navigation

Work answers to a user need. Product requirements and user stories live under `docs/project/`:
- **Product Requirement Records (PRDs)**: `docs/project/product/`. PRDs move through `idea/`, `shaped/`, `accepted/`, and `shipped/`.[^18]
- **User Stories**: `docs/project/user_stories/`. User stories define end-to-end value from the persona perspective (Player, DM, Absent Player, Spectator, Developer).[^19]

A product record states a need and checkable outcomes; it never dictates internal code structure. Architectural decisions belong in ADRs.[^3]

## Task Management

Engineering work lives in `docs/project/backlog/`.[^20] An item moves through three directories:
- `proposed/`: Unrefined ideas and candidate work items.
- `refined/`: Architectural impact review completed, governing ADRs cited, testable definition of done established.
- `complete/`: Verified against tests, linted, committed, and integrated.

Always pick the highest-priority item from `docs/project/backlog/PRIORITY.md` that is in `refined/`.[^21]

## Documentation Directory & Agent Instructions

All system documentation outside project records lives in `docs/` and strictly follows the Diataxis framework:[^22] Agents must consult these guides before writing code or modifying structures:

### Agent Directives on Documentation
- **Inform work with existing docs**: Always search and use documentation references in `docs/` to guide technical design and implementation. Never invent conventions or structures that contradict existing records.
- **Fix inaccurate or stale docs**: If an existing document is incorrect, outdated, or incomplete, fix it as part of your change. Leaving known doc errors in place is a defect.
- **Produce docs for generic / reusable patterns**: If you are implementing capabilities that will be generally or generically applied across services or integrated in multiple places (e.g. auth middleware, tracing, storage pipelines, client SDKs), you must author corresponding Diataxis guides (`docs/how-to/` or `docs/reference/`) when none exist.

### 1. Tutorials (`docs/tutorials/`) — Learning-Oriented
- [`01-local-development-setup.md`](docs/tutorials/01-local-development-setup.md): Complete setup for local Kind cluster, Helm stack, UV monorepo, and Storybook.
- [`02-running-your-first-session.md`](docs/tutorials/02-running-your-first-session.md): Walkthrough of running an interactive tabletop session with The Watcher.

### 2. How-To Guides (`docs/how-to/`) — Practical Recipes & Instructions
- [`create-a-new-service-bc.md`](docs/how-to/create-a-new-service-bc.md): How to scaffold a new bounded context microservice and wire it into Helm and UV.
- [`define-event-sourced-aggregates.md`](docs/how-to/define-event-sourced-aggregates.md): How to define declarative aggregates and handle domain events with `eventsource-py`.
- [`define-spicedb-zanzibar-permissions.md`](docs/how-to/define-spicedb-zanzibar-permissions.md): How to define schema relations in `runefoble.zed`, write tuples, and check permissions.
- [`develop-lit-components-in-storybook.md`](docs/how-to/develop-lit-components-in-storybook.md): How to develop Lit Web Components in Storybook with Bauhaus design tokens.
- [`add-a-watcher-ai-tool.md`](docs/how-to/add-a-watcher-ai-tool.md): How to expose new FastMCP tabletop tools and session resources to LLM agents.
- [`curate-backlog-and-roadmap.md`](docs/how-to/curate-backlog-and-roadmap.md): How to triage the backlog, evaluate INVEST criteria, scan file invariants, and perform JIT refinement.
- [`decompose-prds-into-vertical-slices.md`](docs/how-to/decompose-prds-into-vertical-slices.md): How to scaffold PRDs, audit backlog buffers, and decompose requirements into single-pass vertical slices and ADR spikes.
- [`instrument-services-with-opentelemetry.md`](docs/how-to/instrument-services-with-opentelemetry.md): How to instrument FastAPI services, configure OTel exporters, and propagate trace context over Redis Streams.
- [`authenticate-with-zitadel-oidc.md`](docs/how-to/authenticate-with-zitadel-oidc.md): How to validate Zitadel JWTs against JWKS discovery, enforce HTTP dependencies, and secure WebSockets.
- [`track-analytics-events.md`](docs/how-to/track-analytics-events.md): How to record privacy-preserving analytics via OpenPanel SDK and Redis Streams workers.
- [`visualize-project-content.md`](docs/how-to/visualize-project-content.md): How to launch the dynamic project content visualizer, trace Redstring dependencies, and export standalone HTML bundles.
- [`decompose-microservice-routers.md`](docs/how-to/decompose-microservice-routers.md): How to decompose monolithic FastAPI microservices into modular APIRouters.
- [`configure-appearance-and-themes.md`](docs/how-to/configure-appearance-and-themes.md): How to configure global themes, appearance color modes (Dark/Light/System), and interact with the settings modal.
- [`interact-with-tactile-board-and-ghost-previews.md`](docs/how-to/interact-with-tactile-board-and-ghost-previews.md): How to use tactile token kinematics, 5-foot distance measuring, difficult terrain/hazards, and spoken ghost previews.
- [`index-campaign-lore-with-redstring.md`](docs/how-to/index-campaign-lore-with-redstring.md): How to ingest worldbuilding documents with redstring, consolidate entity aliases, and run hybrid RAG queries.
- [`balance-combat-encounters-and-query-compendium.md`](docs/how-to/balance-combat-encounters-and-query-compendium.md): How to query canonical SRD rules with sub-50ms redstring search, balance combat encounters, and register homebrew rules.
- [`forge-procedural-battlemaps-and-tokens.md`](docs/how-to/forge-procedural-battlemaps-and-tokens.md): How to forge procedural battlemaps and tokens with natural language prompts, extract line-of-sight walls and hazards, and project geometry to board_state.
- [`manage-dynamic-soundscapes-and-audio-ducking.md`](docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md): How to calculate encounter tension, crossfade audio stems, trigger tactical foley cues, and coordinate -12dB WebAudio ducking.
- [`configure-stand-in-guardrails-and-hot-swap.md`](docs/how-to/configure-stand-in-guardrails-and-hot-swap.md): How to configure tactical guardrails for absent player stand-ins, zero-HP stabilization, and execute mid-session hot-swap takeover.
- [`manage-dm-copilot-whispers-and-veto-overrides.md`](docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md): How to manage private DM narrative whisper channels, intercept AI mutations, and exercise one-click veto/edit overrides.
- [`resolve-conversational-disambiguation-and-combos.md`](docs/how-to/resolve-conversational-disambiguation-and-combos.md): How to detect ambiguous targets, generate clarification prompts, chain compound action combos, and coordinate rollback.
- [`orchestrate-audience-chaos-polls.md`](docs/how-to/orchestrate-audience-chaos-polls.md): How to configure and orchestrate live audience chaos polls, ingest spectator votes across streaming channels, and manage DM approval queues.
- [`import-universal-vtt-maps-and-register-dynamic-tools.md`](docs/how-to/import-universal-vtt-maps-and-register-dynamic-tools.md): How to import community Universal VTT maps (.dd2vtt), extract line-of-sight walls, store battlemap textures in Silo S3, and register dynamic runtime FastMCP tools.
- [`broadcast-obs-stream-overlay-and-cinematic-camera.md`](docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md): How to embed the alpha-transparent OBS party vitals HUD overlay, configure cubic-bezier cinematic director tracking, and sanitize DM secrets.
- [`project-campaign-analytics-and-chronicle-timeline.md`](docs/how-to/project-campaign-analytics-and-chronicle-timeline.md): How to project combat telemetry, query spatial damage heatmaps, calculate encounter MVP awards, and view chronicle timelines.
- [`interact-with-character-sheet-and-inventory.md`](docs/how-to/interact-with-character-sheet-and-inventory.md): How to interact with character sheet equipment slots, inventory encumbrance, condition tooltips, and spell slot tracking.
- [`run-campfire-rests-and-alchemical-crafting.md`](docs/how-to/run-campfire-rests-and-alchemical-crafting.md): How to combine reagents with volatile mishap tables, resolve campfire resting boons, and manage party stronghold upgrades.
- [`run-tavern-minigames-and-merchant-haggling.md`](docs/how-to/run-tavern-minigames-and-merchant-haggling.md): How to run interactive Liar's Dice wagering, drinking contests with DSP voice filters, and negotiate with personality-driven merchants.
- [`inspect-diegetic-handouts-and-3d-relics.md`](docs/how-to/inspect-diegetic-handouts-and-3d-relics.md): How to generate diegetic parchment handouts, break wax seals with acoustic feedback, reveal UV invisible ink runes, and inspect 3D WebGL relics.
- [`forge-print-ready-maps-standees-and-stl-tokens.md`](docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md): How to forge multi-page 1-inch grid PDFs, foldable papercraft standees, and watertight 3D STL token rings with status clips.
- [`interact-with-campaign-atlas-and-codex.md`](docs/how-to/interact-with-campaign-atlas-and-codex.md): How to navigate the multi-layered world atlas, define geopolitical boundaries, place milestone pins with era filtering, and manage private/shared party codex notes.
- [`manage-generative-wardrobe-and-condition-portraits.md`](docs/how-to/manage-generative-wardrobe-and-condition-portraits.md): How to synthesize narrative wardrobe variants, apply real-time condition overlays (bloodied, poisoned, stunned), and synchronize board tokens.


### 3. Technical Reference (`docs/reference/`) — Specifications & Architecture
- [`architecture-overview.md`](docs/reference/architecture-overview.md): Macro architecture, system boundaries, and cross-service data flows.
- [`platform-services.md`](docs/reference/platform-services.md): Directory of external platform services, container images, ports, environment variables, and test fallbacks.
- [`ports-and-endpoints.md`](docs/reference/ports-and-endpoints.md): Ingress routing table, microservice ports, core HTTP routes, and infrastructure ports.
- [`events-schema.md`](docs/reference/events-schema.md): CloudEvents domain events catalogue, payload schemas, and Redis Stream topics.
- [`diegetic-handouts-and-relics-events.md`](docs/reference/diegetic-handouts-and-relics-events.md): CloudEvents schemas and payloads for diegetic handouts, breakable wax seals, and 3D relics.
- [`downtime-and-crafting-events.md`](docs/reference/downtime-and-crafting-events.md): CloudEvents schemas and event flows for downtime crafting, rests, and stronghold facilities.
- [`tavern-and-merchants-events.md`](docs/reference/tavern-and-merchants-events.md): CloudEvents schemas and event flows for tavern minigames, drinking contests, and merchant haggling.
- [`redis-streams-event-bus.md`](docs/reference/redis-streams-event-bus.md): Redis Streams transport architecture, channel conventions, and consumer groups.
- [`design-tokens-and-themes.md`](docs/reference/design-tokens-and-themes.md): Bauhaus geometric tokens, typography, CSS custom properties, and UI themes.
- [`fastmcp-gateway.md`](docs/reference/fastmcp-gateway.md): Model Context Protocol gateway architecture, tool inventory, resources, and prompt templates.
- [`cli-interfaces.md`](docs/reference/cli-interfaces.md): Developer tooling, `Makefile` targets, `uv` commands, and Antigravity slash commands.

### 4. Architecture Explanation (`docs/explanation/`) — Design Rationale & Background
- [`the-watcher-autonomous-dm.md`](docs/explanation/the-watcher-autonomous-dm.md): Rationale behind The Watcher AI DM, intent extraction, and DM veto authority.
- [`zanzibar-in-ttrpg.md`](docs/explanation/zanzibar-in-ttrpg.md): Design rationale for using Google Zanzibar / SpiceDB fine-grained authorization in tabletop RPGs.
- [`realtime-voice-and-board-sync.md`](docs/explanation/realtime-voice-and-board-sync.md): Sub-500ms pipeline architecture, audio streaming, WebSockets, and optimistic client synchronization.

## Repository Layout

| Path | Contents |
|---|---|
| `libs/runefoble_platform/` | Common models, config, error hierarchy, event bus |
| `libs/runefoble_auth/` | Zitadel JWT decoding, SpiceDB Zanzibar client, `runefoble.zed` schema |
| `libs/runefoble_events/` | CloudEvents-compliant domain event definitions |
| `services/the_watcher/` | The Watcher AI gameplay engine (speech-to-intent, DM, AI stand-ins) & microfrontend |
| `services/game_session/` | Active session lifecycle, turns, player presence, dice & microfrontends |
| `services/board_state/` | Tactical grid, token coordinates, spatial movement rules & board microfrontend |
| `services/character_sheet/` | Character stats, HP tracking, session absence penalties & character microfrontends |
| `services/voice_agent/` | Audio streaming, STT/TTS pipeline, voice persona synthesis & voice controls microfrontend |
| `services/campaign_lore/` | Worldbuilding knowledge graphs, entity alias consolidation & redstring hybrid RAG microservice |
| `services/rules_compendium/` | TTRPG rules compendium, sub-50ms redstring hybrid retrieval & automated CR encounter builder |
| `services/asset_forge/` | Procedural battlemap diffusion synthesis, wall/hazard geometry extraction & token portrait generator |
| `services/soundscape/` | Dynamic audio stem mixing, tactical foley cues, tension scoring & audio controls microfrontend |
| `services/audience_studio/` | TypeScript audience interactivity engine, live chaos polls, DM approval queue & microfrontend |
| `services/campaign_analytics/` | Combat telemetry, tactical heatmaps, MVP turn statistics & chronicle timeline archive |
| `gateway/api/` | Unified API Gateway, WebSockets, OpenAPI aggregator |
| `gateway/mcp/` | Model Context Protocol server exposing tools to LLM models |
| `frontend/` | Lightweight App Shell, global themes/layout, Storybook design system aggregator |
| `deployments/helm/` | Umbrella Helm chart for Kubernetes deployment |
| `deployments/kind/` | Kind Kubernetes cluster configuration for local development |
| `docs/project/` | ADRs, PRDs, User Stories, and Backlog records |
| `docs/` | Diataxis documentation (tutorials, how-to, reference, explanation) |
| `Makefile` | Developer interface targets (`cluster-up`, `dev-storybook`, `test`) |

## Definition of Ready (DoR)

A backlog task or feature may only be transitioned to `refined/` and pulled into active development when:
1. **Documentation Review**: Relevant existing documentation in `docs/` has been reviewed and explicitly considered during planning.
2. **Bounded Context & Microfrontends**: Target service bounded context (`services/<bc>`) is designated, and for any user-facing feature, the owning UI package (`services/<bc>/ui/`) and Custom Element tags (`<runefoble-...>`) are defined.[^25]
3. **Reference PRD Cited**: A governing Product Requirement Document in `docs/project/product/accepted/` is linked to establish the user need and business value.[^18]
4. **User Stories Linked**: Persona-driven user stories in `docs/project/user_stories/accepted/` are linked to anchor acceptance criteria.[^19]
5. **Architectural Review**: Governing ADRs in `docs/project/adrs/accepted/` (e.g. ADR-0004, ADR-0012, ADR-0013) are cited and technical impact on existing boundaries evaluated.[^3][^25]
6. **INVEST Criteria Satisfied**: The task is validated against INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small [<500 lines per file], Testable).[^20]
7. **Frontdoor Blackbox Test Plan**: Frontdoor test scenarios and setup are clearly specified, interacting strictly via public HTTP endpoints, WebSockets, or CloudEvents.

## Definition of Done (DoD)

Work is complete only when:
1. **Architectural Alignment**: Verified against governing ADRs (including ADR-0013 for microfrontends) without backdoor state manipulation.[^3][^25]
2. **Microfrontend Vendoring**: Any user-facing components are built and vendored inside their owning service bounded context (`services/<bc>/ui/`), exposed via `/ui/manifest`, with the App Shell (`frontend/`) remaining strictly decoupled.[^25]
3. **Frontend Storybook Verification**: UI components built with Shadow DOM and Bauhaus design tokens, accompanied by interactive Storybook stories with zero console errors.[^13]
4. **Documentation Integrity**:
   - Inaccurate or stale docs discovered during work are corrected.
   - New Diataxis guides (`docs/how-to/` or `docs/reference/`) are created if introducing generic patterns, microfrontends, or cross-service capabilities.
   - All new public APIs, events, and microfrontend custom elements are documented in `docs/reference/`.[^12]
5. **Blackbox TDD Suite with Frontdoor Setup**: All scenarios verified through public entrypoints (HTTP routes, WebSockets, standard domain events) rather than private internals or backdoor state manipulation.
6. **Automated Verification Gates**: All Python tests pass via `uv run pytest`, frontend builds pass via `pnpm run build` and `make build`, and `make health-check` passes.[^23]
7. **Helm & Kubernetes Integrity**: Umbrella Helm chart passes `helm lint` and renders cleanly via `helm template`.[^4]
8. **Registry & Backlog Synchronization**: Registries in `docs/project/` (PRDs and User Stories) updated to reflect the new state.[^18] For Backlog items (`complete/` and `PRIORITY.md`), updates are applied atomically upon integration into `main` by the integration orchestrator (never directly on feature branches or in worker worktrees to prevent merge conflicts).
9. **Changelog Maintenance**: User-facing capabilities, architectural shifts, and public API/schema changes are recorded in `CHANGELOG.md` under `[Unreleased]` following the Keep a Changelog standard.
10. **File Length Limit**: Strictly enforced with zero source files exceeding ~500 lines.

## Dispatching Work to Agents & Parallel Worktrees

When delegating tasks to subagents:
1. **Ask each agent for the complete change**: implementation, frontdoor blackbox tests, and Diataxis documentation.
2. **Isolate concurrent workstreams using Git worktrees**:
   - Create an isolated worktree branch: `git worktree add -b <feature-branch> .worktrees/<feature-name> main`.
   - Direct the subagent to perform all edits and runs within its designated worktree directory.
   - Upon completion, merge the feature branch back to `main`, verify gates, and clean up the worktree (`git worktree remove .worktrees/<feature-name> && git branch -d <feature-branch>`).
3. **Spin an agent down when it hands back**: do not reuse agents across disparate workstreams.
4. **Trust what an agent says it did, but verify what it worked out**: confirm tests run green and build gates pass.
5. **Maintain PRDs and user stories**: Subagents must proactively maintain relevant PRDs (in `docs/project/product/`) and user stories. Backlog progression (moving from `refined/` to `complete/` and marking `(Complete)` in `PRIORITY.md`) is handled exclusively by the orchestrator upon merge to `main` to ensure zero merge conflicts across parallel worktrees.

## References

[^1]: Bootstrap task completion record. `docs/project/backlog/complete/0000-bootstrap-repository-and-foundations.md`
[^2]: Repository architecture overview. `docs/reference/architecture-overview.md`
[^3]: ADR Registry. `docs/project/adrs/REGISTRY.md`
[^4]: Kubernetes and Helm infrastructure ADR. `docs/project/adrs/accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md`
[^5]: Zitadel identity integration. `libs/runefoble_auth/src/runefoble_auth/zitadel.py`
[^6]: SpiceDB Zanzibar authorization ADR. `docs/project/adrs/accepted/adr-0001-spicedb-zanzibar-object-authorization.md`
[^7]: Database configuration. `libs/runefoble_platform/src/runefoble_platform/config.py`
[^8]: Silo S3 configuration. `deployments/helm/runefoble/templates/silo.yaml`
[^9]: OpenPanel analytics configuration. `deployments/helm/runefoble/templates/openpanel.yaml`
[^10]: Observability configuration. `deployments/helm/runefoble/templates/observability.yaml`
[^11]: Swagger UI aggregator. `deployments/helm/runefoble/templates/swagger-ui.yaml`
[^12]: Events schema reference. `docs/reference/events-schema.md`
[^13]: Frontend Lit and Storybook ADR. `docs/project/adrs/accepted/adr-0004-lit-web-components-and-storybook-ui.md`
[^14]: UV workspace monorepo ADR. `docs/project/adrs/accepted/adr-0003-uv-monorepo-workspace-for-python-bcs.md`
[^15]: Realtime voice and board sync. `docs/explanation/realtime-voice-and-board-sync.md`
[^16]: The Watcher Autonomous DM architecture. `docs/explanation/the-watcher-autonomous-dm.md`
[^17]: Missing player stand-in PRD. `docs/project/product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md`
[^18]: Product requirements registry. `docs/project/product/REGISTRY.md`
[^19]: User stories registry. `docs/project/user_stories/REGISTRY.md`
[^20]: Backlog guide. `docs/project/backlog/README.md`
[^21]: Backlog priority index. `docs/project/backlog/PRIORITY.md`
[^22]: Diataxis documentation framework. `https://diataxis.fr/`
[^23]: Developer Makefile interfaces. `Makefile`
[^24]: eventsource-py architecture ADR. `docs/project/adrs/accepted/adr-0011-eventsource-py-core-event-sourcing.md`
[^25]: Microfrontend Architecture and Service Component Vendoring ADR. `docs/project/adrs/accepted/adr-0013-microfrontend-architecture-and-service-component-vendoring.md`
