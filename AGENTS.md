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
3. **Frontend components are built and tested in Storybook first.** Build new UI elements as Lit Web Components in `frontend/src/components/` and verify them in `frontend/src/stories/` before embedding them into application views.[^13]
4. **All Python packages are managed through the root UV workspace.** Do not use pip, poetry, or virtualenvs directly. Run commands through `uv` or the developer `Makefile`.[^14]
5. **Services publish OpenAPI specs to the Swagger UI hub.** Every new HTTP service must expose `/openapi.json` and register its URL in `deployments/helm/runefoble/values.yaml`.[^11]

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

## Diataxis Documentation Framework

Documentation outside project management lives in `docs/` and strictly follows the Diataxis framework:[^22]
- **Tutorials (`docs/tutorials/`)**: Learning-oriented lessons guiding a newcomer to success (e.g. spinning up Kind, running a first session).
- **How-To Guides (`docs/how-to/`)**: Goal-oriented recipes solving practical problems (e.g. creating a service BC, defining SpiceDB permissions).
- **Reference (`docs/reference/`)**: Information-oriented technical descriptions (e.g. architecture overview, events schema, ports, CLI).
- **Explanation (`docs/explanation/`)**: Understanding-oriented discussions of architecture rationale (e.g. The Watcher AI DM, Zanzibar in TTRPG).

## Repository Layout

| Path | Contents |
|---|---|
| `libs/runefoble_platform/` | Common models, config, error hierarchy, event bus |
| `libs/runefoble_auth/` | Zitadel JWT decoding, SpiceDB Zanzibar client, `runefoble.zed` schema |
| `libs/runefoble_events/` | CloudEvents-compliant domain event definitions |
| `services/the_watcher/` | The Watcher AI gameplay engine (speech-to-intent, DM, AI stand-ins) |
| `services/game_session/` | Active session lifecycle, turns, player presence |
| `services/board_state/` | Tactical grid, token coordinates, spatial movement rules |
| `services/character_sheet/` | Character stats, HP tracking, session absence penalties |
| `services/voice_agent/` | Audio streaming, STT/TTS pipeline, voice persona synthesis |
| `gateway/api/` | Unified API Gateway, WebSockets, OpenAPI aggregator |
| `gateway/mcp/` | Model Context Protocol server exposing tools to LLM models |
| `frontend/` | Lit Web Components, Vite application, Storybook design system |
| `deployments/helm/` | Umbrella Helm chart for Kubernetes deployment |
| `deployments/kind/` | Kind Kubernetes cluster configuration for local development |
| `docs/project/` | ADRs, PRDs, User Stories, and Backlog records |
| `docs/` | Diataxis documentation (tutorials, how-to, reference, explanation) |
| `Makefile` | Developer interface targets (`cluster-up`, `dev-storybook`, `test`) |

## Definition of Done

Work is complete only when:
1. Architectural impact review was conducted against governing ADRs.[^3]
2. All new public APIs and events are documented in `docs/reference/`.[^12]
3. Frontend components have interactive stories in Storybook with zero console errors.[^13]
4. Python tests pass via `uv run pytest` and frontend builds pass via `pnpm run build`.[^23]
5. Helm chart passes linting via `helm lint` and renders cleanly via `helm template`.[^4]
6. Registries in `docs/project/` are updated to reflect the new state.[^18]

## Dispatching Work to Agents

When delegating tasks to subagents:
1. **Ask each agent for the complete change**: implementation, tests, and documentation.
2. **Give each agent an isolated workspace** (e.g. `Workspace: 'share'` for worktrees).
3. **Spin an agent down when it hands back**: do not reuse agents across disparate workstreams.
4. **Trust what an agent says it did, but verify what it worked out**: confirm tests run green and build gates pass.

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
