# Microfrontend Architecture Reference

Runefoble implements a **Microfrontend Architecture** adhering to Domain-Driven Design (DDD) principles. User interface presentation components are strictly owned and vendored by their respective service bounded contexts, while `frontend/` functions as the lightweight **App Shell**.

## Architectural Layout

```
runefoble/
├── frontend/                     # Lightweight App Shell
│   ├── src/
│   │   ├── runefoble-app.ts      # Top-level shell layout, header & WebSocket orchestration
│   │   ├── components/           # Shell components & backward-compatible re-exports
│   │   │   └── runefoble-theme-switcher.ts  # Bauhaus modernist theme switcher
│   │   └── styles/
│   │       └── themes.css        # Bauhaus default tokens & alternative palettes
│   └── .storybook/               # Global Storybook studio aggregating all microfrontends
│
├── services/
│   ├── board_state/ui/           # @runefoble/board-state-ui
│   │   └── src/
│   │       ├── runefoble-board.ts
│   │       └── runefoble-board.stories.ts
│   ├── character_sheet/ui/       # @runefoble/character-sheet-ui
│   │   └── src/
│   │       ├── runefoble-character-card.ts
│   │       └── runefoble-absentee-recap.ts
│   ├── game_session/ui/          # @runefoble/game-session-ui
│   │   └── src/
│   │       ├── runefoble-initiative-tracker.ts
│   │       ├── runefoble-dice-roller.ts
│   │       ├── runefoble-spectator-view.ts
│   │       └── utils/dice.ts
│   ├── the_watcher/ui/           # @runefoble/the-watcher-ui
│   │   └── src/
│   │       ├── runefoble-watcher-feed.ts
│   │       └── runefoble-autonomous-dm.ts
│   └── voice_agent/ui/           # @runefoble/voice-agent-ui
│       └── src/
│           ├── runefoble-voice-controls.ts
│           └── runefoble-voice-controls.stories.ts
```

## Service Microfrontend Catalog

| Service Bounded Context | NPM Package Name | Vendored Custom Elements | Storybook Story Path |
|---|---|---|---|
| `board_state` | `@runefoble/board-state-ui` | `<runefoble-board>` | `services/board_state/ui/src/runefoble-board.stories.ts` |
| `character_sheet` | `@runefoble/character-sheet-ui` | `<runefoble-character-card>`, `<runefoble-absentee-recap>` | `services/character_sheet/ui/src/*.stories.ts` |
| `game_session` | `@runefoble/game-session-ui` | `<runefoble-initiative-tracker>`, `<runefoble-dice-roller>`, `<runefoble-spectator-view>` | `services/game_session/ui/src/*.stories.ts` |
| `the_watcher` | `@runefoble/the-watcher-ui` | `<runefoble-watcher-feed>`, `<runefoble-autonomous-dm>` | `services/the_watcher/ui/src/*.stories.ts` |
| `voice_agent` | `@runefoble/voice-agent-ui` | `<runefoble-voice-controls>` | `services/voice_agent/ui/src/runefoble-voice-controls.stories.ts` |
| `frontend` (App Shell) | `frontend` | `<runefoble-app>`, `<runefoble-theme-switcher>` | `frontend/src/stories/theme-switcher.stories.ts` |

## Pnpm Monorepo Workspace

The monorepo workspace links packages using standard pnpm workspace protocols:

```yaml
# pnpm-workspace.yaml
packages:
  - 'frontend'
  - 'services/*/ui'

allowBuilds:
  esbuild: true
```

The App Shell declares workspace dependencies inside `frontend/package.json`:

```json
{
  "dependencies": {
    "@runefoble/board-state-ui": "workspace:*",
    "@runefoble/character-sheet-ui": "workspace:*",
    "@runefoble/game-session-ui": "workspace:*",
    "@runefoble/the-watcher-ui": "workspace:*",
    "@runefoble/voice-agent-ui": "workspace:*",
    "lit": "^3.3.3"
  }
}
```

## HTTP Frontdoor Discovery (`GET /ui/manifest`)

Each service exposes an HTTP endpoint on its FastAPI frontdoor declaring its microfrontend metadata:

```bash
curl http://localhost:8002/ui/manifest
```

Response:
```json
{
  "service": "board_state",
  "package": "@runefoble/board-state-ui",
  "components": ["runefoble-board"],
  "version": "0.1.0"
}
```

## Storybook Dynamic Aggregation

`frontend/.storybook/main.ts` automatically discovers stories across the monorepo:

```typescript
stories: [
  '../src/**/*.stories.@(js|jsx|mjs|ts|tsx)',
  '../../services/*/ui/src/**/*.stories.@(js|jsx|mjs|ts|tsx)',
]
```

This enforces **Hard Invariant 3**: components are developed and visually verified in Storybook isolation before being mounted into the App Shell.
