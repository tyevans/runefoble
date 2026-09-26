---
icon: lucide/book-open
---

# Runefoble Platform Documentation

> **Runefoble** is an imaginative gaming platform for storytellers of all ages — a collaborative tabletop roleplaying service powered by advanced AI.

Speak and the board obeys: natural speech is parsed into game actions and applied directly to the game state, while The Watcher and the Game Master explore the narrative consequences. Real-time board animations, collaborative chat, voice streaming, autonomous DMing, and missing player AI stand-ins (with humorous DM penalties like "drunk" and "foolishness") are core capabilities.

---

## 🗺️ Visual Architecture & Traceability

<div class="grid cards" markdown>

-   :material-bullhorn: **[Platform Showcase & Vision](marketing.md)**

    ---

    Explore Runefoble's core capabilities, tactical board innovations, voice-driven AI DM, and the forward-looking product roadmap.

-   :material-graph: **[Interactive Project Visualizer](project-visualizer.md)**

    ---

    Explore the live 2D force-directed dependency graph, cyber-flow DAG, concentric radar, Kanban delivery pipeline, and milestone Gantt timeline.

-   :material-palette: **[Storybook UI Studio](storybook-studio.md)**

    ---

    Interactive component studio for all Lit Web Components across service microfrontends, Bauhaus design tokens, and theme matrices.

-   :material-robot: **[Operating Manual for AI Agents](operating-manual.md)**

    ---

    Repository invariants, architectural rules, Definition of Ready (DoR), and Definition of Done (DoD) governing development.

</div>

---

## 📚 Diataxis Documentation System

The Runefoble system documentation is organized strictly according to the **Diataxis framework**:

<div class="grid cards" markdown>

-   :material-school: **[Tutorials](tutorials/01-local-development-setup.md)**

    ---

    Learning-oriented lessons to get you started:
    * [01. Local Development Setup](tutorials/01-local-development-setup.md)
    * [02. Running Your First Session](tutorials/02-running-your-first-session.md)

-   :material-wrench: **[How-To Guides](how-to/visualize-project-content.md)**

    ---

    Practical recipes and task-oriented instructions:
    * [Visualize Project Content](how-to/visualize-project-content.md)
    * [Define SpiceDB Zanzibar Permissions](how-to/define-spicedb-zanzibar-permissions.md)
    * [Define Event-Sourced Aggregates](how-to/define-event-sourced-aggregates.md)
    * [Develop Lit Components in Storybook](how-to/develop-lit-components-in-storybook.md)
    * [Instrument Services with OpenTelemetry](how-to/instrument-services-with-opentelemetry.md)
    * [Authenticate with Zitadel OIDC](how-to/authenticate-with-zitadel-oidc.md)

-   :material-file-code: **[Technical Reference](reference/architecture-overview.md)**

    ---

    Information-oriented specifications and technical registries:
    * [Architecture Overview](reference/architecture-overview.md)
    * [Microfrontend Architecture](reference/microfrontend-architecture.md)
    * [Ports & Endpoints Routing Table](reference/ports-and-endpoints.md)
    * [Events Schema (CloudEvents)](reference/events-schema.md)
    * [Redis Streams Event Bus](reference/redis-streams-event-bus.md)
    * [Design Tokens & Themes](reference/design-tokens-and-themes.md)
    * [FastMCP Tabletop Gateway](reference/fastmcp-gateway.md)
    * [CLI Interfaces & Developer Tools](reference/cli-interfaces.md)

-   :material-lightbulb-on: **[Architecture Explanation](explanation/the-watcher-autonomous-dm.md)**

    ---

    Understanding-oriented design rationale:
    * [The Watcher Autonomous DM](explanation/the-watcher-autonomous-dm.md)
    * [Google Zanzibar in Tabletop RPG](explanation/zanzibar-in-ttrpg.md)
    * [Microfrontends in RPG Domains](explanation/microfrontends-in-rpg-domains.md)
    * [Realtime Voice & Board Sync](explanation/realtime-voice-and-board-sync.md)

</div>

---

## 📋 Architecture Decisions & Project Records

Formal project management records and specifications live under `docs/project/`:

* **[Architectural Decision Records (ADRs)](project/adrs/REGISTRY.md)**: 13+ accepted architectural records governing data structures, infrastructure, and authorization.
* **[Product Requirements Documents (PRDs)](project/product/REGISTRY.md)**: Core capabilities, feature matrices, and capability inventories.
* **[User Stories & Personas](project/user_stories/REGISTRY.md)**: Persona-driven scenarios and acceptance criteria.
* **[Engineering Backlog & Priorities](project/backlog/PRIORITY.md)**: Backlog items, milestone roadmap horizons, and autonomous backlog engine tasks.
* **[Platform Changelog](changelog.md)**: Historical release notes and unreleased capabilities following Keep a Changelog.
