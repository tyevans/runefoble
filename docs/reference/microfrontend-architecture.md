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
│   │       ├── runefoble-board.stories.ts
│   │       ├── runefoble-map-uploader.ts
│   │       └── runefoble-map-uploader.stories.ts
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
| `board_state` | `@runefoble/board-state-ui` | `<runefoble-board>`, `<runefoble-map-uploader>` | `services/board_state/ui/src/*.stories.ts` |
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
  "components": ["runefoble-board", "runefoble-map-uploader"],
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

## Component Specification: `<runefoble-voice-controls>`

The `@runefoble/voice-agent-ui` package vendors `<runefoble-voice-controls>` for collaborative WebRTC audio streaming, live microphone input levels, and real-time waveform visualization.

### Properties & Attributes

| Property | Type | Default | Description |
|---|---|---|---|
| `isListening` | `boolean` | `false` | Microphone streaming / push-to-talk active state. |
| `disabled` | `boolean` | `false` | Disables mic controls. |
| `channelName` | `string` | `'Collaborative Voice Channel'` | Display name of the active audio room. |
| `connectionState` | `'disconnected' \| 'connecting' \| 'connected' \| 'reconnecting' \| 'failed'` | `'disconnected'` | WebRTC peer connection status. |
| `bandwidthQuality` | `'good' \| 'low' \| 'degraded'` | `'good'` | Network transmission condition. |
| `bitrateKbps` | `number` | `64` | Current streaming bitrate in kbps. |
| `packetsLost` | `number` | `0` | Cumulative WebRTC packet loss count. |
| `latencyMs` | `number` | `24` | Round-trip transmission latency. |
| `activeFilters` | `string[]` | `[]` | Active audio DSP afflictions (e.g. `'drunk'`, `'whisper'`). |
| `simulated` | `boolean` | `false` | Enable simulated harmonic waveform generation (for Storybook / testing). |

### Dispatched CustomEvents

| Event Name | Detail Payload | Description |
|---|---|---|
| `voice-toggle` | `{ isListening: boolean }` | Dispatched when the user clicks the mic button. |
| `voice-state` | `{ isListening: boolean, connectionState: string, bandwidthQuality: string, activeFilters: string[] }` | Dispatched when streaming, connection state, or DSP filters change. |
| `voice-level` | `{ level: number, peak: number }` | Emitted per animation frame with normalized audio input RMS (0.0 - 1.0) and peak. |

### Visualizer & WebRTC Monitor
- **WebAudio `AnalyserNode` Loop**: Renders 60fps reactive waveforms to an HTML5 `<canvas>` element using time-domain data (or simulated harmonic synthesis during tests / absence of physical mic).
- **Affliction DSP Styling**: Adapts waveform stroke color to Canary Yellow (`var(--rf-accent-tertiary, #ffb703)`) and introduces drunken phase wobbles when inebriation filters are active.
- **Low Bandwidth Warning**: Highlights degraded WebRTC channels (`bandwidthQuality === 'low'` or `packetsLost > 5`) with a pulsing warning badge.

