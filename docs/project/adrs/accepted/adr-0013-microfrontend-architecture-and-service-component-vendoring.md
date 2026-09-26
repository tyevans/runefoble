# ADR-0013: Microfrontend Architecture and Service Component Vendoring

## Status
Accepted

## Context
Runefoble's user interface was initially constructed as a set of Lit Web Components within a centralized `frontend/src/components/` directory (governed by ADR-0004). As the platform has expanded into distinct Domain-Driven Design (DDD) bounded contexts (`board_state`, `character_sheet`, `game_session`, `the_watcher`, and `voice_agent`), this monolithic frontend structure caused architectural friction:

1. **Violation of Bounded Context Boundaries**: Domain presentation rules (tactical fog-of-war shaders, session absence penalty badges, dice physics arithmetic, and voice visualizers) were disconnected from their governing domain services and aggregates.
2. **Coupling and Bloat**: Changes to domain features required simultaneous edits across disparate directories (`services/` and `frontend/src/components/`), and the main application shell (`frontend/src/runefoble-app.ts`) accumulated domain-specific rendering logic, exceeding healthy file-length invariants.
3. **Autonomous Team Ownership**: In a vertical-slice microservice architecture, each domain service must own its entire lifecycle: domain models, eventsource-py aggregates, public REST/WebSocket APIs, and frontend user interface elements.

## Decision
We adopt a **Microfrontend Architecture** across the platform with **Service Component Vendoring**:

1. **Frontend as Pure App Shell**:
   - `frontend/` is restricted to being the host **App Shell** (`runefoble-app`).
   - The shell provides top-level chrome: branding header, session metadata badges, mode switching (Party Mode vs. Spectator Mode), and the responsive CSS grid layout.
   - The shell hosts global design tokens and theming controls (`themes.css` and `<runefoble-theme-switcher>`), as established in ADR-0012.
   - The shell acts as the event and communication multiplexer: connecting to session WebSockets and dispatching events to embedded microfrontends.

2. **Service Bounded Context Component Ownership (`services/<bc>/ui/`)**:
   Each service bounded context is the authoritative owner and vendor of its frontend components:
   - `services/board_state/ui/`: Vendors `<runefoble-board>` (tactical grid, token movement, fog-of-war, hazards).
   - `services/character_sheet/ui/`: Vendors `<runefoble-character-card>` and `<runefoble-absentee-recap>` (character stats, HP, conditions, session absence penalties).
   - `services/game_session/ui/`: Vendors `<runefoble-initiative-tracker>`, `<runefoble-dice-roller>`, `<runefoble-spectator-view>`, and client-side dice calculation utilities.
   - `services/the_watcher/ui/`: Vendors `<runefoble-watcher-feed>` and `<runefoble-autonomous-dm>` (chronicle logs, speech transcripts, autonomous DM interventions).
   - `services/voice_agent/ui/`: Vendors `<runefoble-voice-controls>` (collaborative push-to-talk, streaming state, audio visualizer).

3. **Lit Web Components as Microfrontend Standard**:
   - All microfrontends are authored as standard W3C Custom Elements using Lit with Shadow DOM encapsulation.
   - Microfrontends declare their interface strictly via DOM attributes/properties and emit standard CustomEvents (`@move-token`, `@voice-toggle`, etc.) composed across the Shadow DOM boundary.
   - Style isolation is guaranteed by the Shadow DOM, while Bauhaus theme tokens (`var(--rf-*)`) seamlessly penetrate shadow roots via standard CSS variable inheritance.

4. **Pnpm Monorepo Workspace Integration**:
   - The repository root defines a unified `pnpm-workspace.yaml` including `frontend` and `services/*/ui`.
   - Each service UI package is named `@runefoble/<bc>-ui` and defines its own `package.json` and `tsconfig.json`.
   - `frontend/package.json` depends on these packages via the `workspace:*` protocol.
   - `frontend/src/components/` provides backward-compatible forwarding re-exports so that legacy imports continue to resolve without breaking changes.

5. **Component-Driven Storybook Aggregation**:
   - Storybook stories are co-located with components inside each service bounded context (`services/<bc>/ui/src/*.stories.ts`).
   - The App Shell's central Storybook runner (`frontend/.storybook/main.ts`) dynamically aggregates stories across all service packages (`../../services/*/ui/src/**/*.stories.@(js|jsx|mjs|ts|tsx)`).
   - All microfrontends must be built and verified in Storybook isolation with zero console errors before shell composition (Hard Invariant 3).

6. **Service HTTP Frontdoor Discovery (`/ui/manifest`)**:
   - Each FastAPI microservice exposes `GET /ui/manifest` advertising its package name, exported custom elements, and version, enabling runtime introspection and service catalog discoverability.

## Consequences

- **Positive**:
  - **Vertical Slice Autonomy**: Domain logic, aggregates, public APIs, and user interface components evolve together inside each service bounded context.
  - **Lightweight App Shell**: `frontend/src/runefoble-app.ts` is reduced in size and complexity, focusing solely on layout, navigation, and event orchestration.
  - **Zero CSS Bleeding & Standard Interoperability**: Lit Custom Elements avoid framework lock-in and memory overhead while allowing any view mode (Party Mode, Spectator Mode, streaming overlays) to embed components effortlessly.
  - **Unified Living Design System**: Storybook discovers and exercises all microfrontends from a single interface while keeping story ownership with the domain teams.
- **Negative**:
  - Monorepo package dependencies must be synchronized via root pnpm workspaces.
  - Cross-component communication must strictly use DOM events or App Shell bus mediation rather than direct internal state references.
