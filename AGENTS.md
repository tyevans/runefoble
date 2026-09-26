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
- [`instrument-services-with-opentelemetry.md`](docs/how-to/instrument-services-with-opentelemetry.md): How to instrument FastAPI services, configure OTel exporters, and propagate trace context over Redis Streams.
- [`authenticate-with-zitadel-oidc.md`](docs/how-to/authenticate-with-zitadel-oidc.md): How to validate Zitadel JWTs against JWKS discovery, enforce HTTP dependencies, and secure WebSockets.
- [`track-analytics-events.md`](docs/how-to/track-analytics-events.md): How to record privacy-preserving analytics via OpenPanel SDK and Redis Streams workers.

### 3. Technical Reference (`docs/reference/`) — Specifications & Architecture
- [`architecture-overview.md`](docs/reference/architecture-overview.md): Macro architecture, system boundaries, and cross-service data flows.
- [`platform-services.md`](docs/reference/platform-services.md): Directory of external platform services, container images, ports, environment variables, and test fallbacks.
- [`ports-and-endpoints.md`](docs/reference/ports-and-endpoints.md): Ingress routing table, microservice ports, core HTTP routes, and infrastructure ports.
- [`events-schema.md`](docs/reference/events-schema.md): CloudEvents domain events catalogue, payload schemas, and Redis Stream topics.
- [`redis-streams-event-bus.md`](docs/reference/redis-streams-event-bus.md): Redis Streams transport architecture, channel conventions, and consumer groups.
- [`design-tokens-and-themes.md`](docs/reference/design-tokens-and-themes.md): Bauhaus geometric tokens, typography, CSS custom properties, and UI themes.
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
8. **Registry & Backlog Synchronization**: Registries in `docs/project/` (PRDs, User Stories, Backlog `complete/`, and `PRIORITY.md`) updated to reflect the new state.[^18]
9. **File Length Limit**: Strictly enforced with zero source files exceeding ~500 lines.

## Dispatching Work to Agents & Parallel Worktrees

When delegating tasks to subagents:
1. **Ask each agent for the complete change**: implementation, frontdoor blackbox tests, and Diataxis documentation.
2. **Isolate concurrent workstreams using Git worktrees**:
   - Create an isolated worktree branch: `git worktree add -b <feature-branch> .worktrees/<feature-name> main`.
   - Direct the subagent to perform all edits and runs within its designated worktree directory.
   - Upon completion, merge the feature branch back to `main`, verify gates, and clean up the worktree (`git worktree remove .worktrees/<feature-name> && git branch -d <feature-branch>`).
3. **Spin an agent down when it hands back**: do not reuse agents across disparate workstreams.
4. **Trust what an agent says it did, but verify what it worked out**: confirm tests run green and build gates pass.
5. **Maintain PRDs and backlog items**: Subagents must proactively maintain relevant PRDs (in `docs/project/product/`) and backlog items (in `docs/project/backlog/` including refinement, status progression, prioritization in `PRIORITY.md`, and registry synchronization).

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
