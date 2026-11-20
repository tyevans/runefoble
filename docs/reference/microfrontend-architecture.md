# Microfrontend Architecture Reference

Runefoble implements a **Microfrontend Architecture** adhering to Domain-Driven Design (DDD) principles. User interface presentation components are strictly owned and vendored by their respective service bounded contexts, while `frontend/` functions as the lightweight **App Shell**.

## Architectural Layout

```
runefoble/
├── frontend/                     # Lightweight App Shell
│   ├── src/
│   │   ├── runefoble-app.ts      # Top-level shell layout, header & WebSocket orchestration
│   │   ├── components/           # Shell components only; no forwarding re-exports (DoR 9)
│   │   │   ├── runefoble-settings-modal.ts  # Bauhaus settings modal with color mode & themes
│   │   │   └── runefoble-theme-switcher.ts  # Bauhaus modernist theme switcher
│   │   └── styles/
│   │       └── themes.css        # Bauhaus default tokens & alternative palettes
│   └── .storybook/               # Global Storybook studio aggregating all microfrontends
│
├── services/
│   ├── board_state/ui/           # @runefoble/board-state-ui
│   │   └── src/
│   │       ├── runefoble-board.ts
│   │       ├── runefoble-board.styles.ts
│   │       ├── runefoble-board-tokens.styles.ts
│   │       ├── runefoble-board.stories.ts
│   │       ├── runefoble-board.stories.fixtures.ts
│   │       ├── templates/
│   │       │   ├── kinematics.template.ts
│   │       │   ├── cell.template.ts
│   │       │   └── overlays.template.ts
│   │       ├── runefoble-map-uploader.ts
│   │       ├── runefoble-map-uploader.styles.ts
│   │       ├── runefoble-map-uploader.stories.ts
│   │       ├── runefoble-map-dropzone.ts
│   │       ├── runefoble-map-dropzone.stories.ts
│   │       ├── runefoble-map-grid-config.ts
│   │       └── runefoble-map-grid-config.stories.ts
│   ├── character_sheet/ui/       # @runefoble/character-sheet-ui
│   │   └── src/
│   │       ├── runefoble-character-card.ts
│   │       ├── runefoble-character-sheet.ts
│   │       ├── runefoble-character-sheet.styles.ts
│   │       ├── runefoble-character-sheet.core.styles.ts
│   │       ├── runefoble-character-sheet.inventory.styles.ts
│   │       ├── runefoble-character-sheet.conditions.styles.ts
│   │       ├── templates/
│   │       │   ├── stats.template.ts
│   │       │   ├── inventory.template.ts
│   │       │   ├── conditions.template.ts
│   │       │   ├── spells.template.ts
│   │       │   └── index.ts
│   │       ├── runefoble-character-sheet.types.ts
│   │       ├── runefoble-character-sheet.stories.ts
│   │       ├── runefoble-absentee-recap.ts
│   │       └── runefoble-absentee-recap.styles.ts
│   ├── game_session/ui/          # @runefoble/game-session-ui
│   │   └── src/
│   │       ├── runefoble-initiative-tracker.ts
│   │       ├── runefoble-initiative-tracker.styles.ts
│   │       ├── runefoble-dice-roller.ts
│   │       ├── runefoble-spectator-view.ts
│   │       ├── runefoble-spectator-view.styles.ts
│   │       └── utils/dice.ts
│   ├── the_watcher/ui/           # @runefoble/the-watcher-ui
│   │   └── src/
│   │       ├── runefoble-watcher-feed.ts
│   │       ├── runefoble-autonomous-dm.ts
│   │       ├── runefoble-autonomous-dm.styles.ts
│   │       ├── runefoble-dm-whisper-bar.ts
│   │       ├── runefoble-faction-radar.ts
│   │       ├── runefoble-faction-radar.styles.ts
│   │       ├── runefoble-faction-radar.stories.ts
│   │       ├── faction_radar/
│   │       │   ├── types.ts
│   │       │   ├── radar-svg.template.ts
│   │       │   ├── bulletin-drawer.template.ts
│   │       │   ├── faction-details.template.ts
│   │       │   └── index.ts
│   │       ├── runefoble-faction-espionage.ts
│   │       ├── runefoble-faction-espionage.styles.ts
│   │       └── runefoble-faction-espionage.stories.ts
│   └── voice_agent/ui/           # @runefoble/voice-agent-ui
│       └── src/
│           ├── runefoble-voice-controls.ts
│           ├── runefoble-voice-controls.styles.ts
│           ├── runefoble-voice-controls.stories.ts
│           ├── runefoble-mobile-companion.ts
│           ├── runefoble-mobile-companion.styles.ts
│           ├── runefoble-mobile-companion.stories.ts
│           └── mobile_companion/
│               ├── audio_stream_controller.ts
│               ├── haptic_ping_panel.ts
│               ├── connection_status_badge.ts
│               └── styles/
```

## Service Microfrontend Catalog

| Service Bounded Context | NPM Package Name | Vendored Custom Elements | Storybook Story Path |
|---|---|---|---|
| `board_state` | `@runefoble/board-state-ui` | `<runefoble-board>` (events `move-token` and `move-rejected`; shows a refused board action, from a server `error` frame or a closed socket, in a `role="alert"` line), `<runefoble-board-empty>` (no-battlemap-yet state; `can-set-up-map` shows the DM hint and the "Set up battlemap" control; properties `campaignId`, `sessionId`, `seats`, `apiBaseUrl`; event `board-set-up` with `{ sessionId, failure }`), `<runefoble-map-uploader>` (subviews: `<runefoble-map-dropzone>`, `<runefoble-map-grid-config>`) | `services/board_state/ui/src/*.stories.ts` |
| `character_sheet` | `@runefoble/character-sheet-ui` | `<runefoble-character-card>`, `<runefoble-character-sheet>`, `<runefoble-absentee-recap>` (defined and exported; the App Shell does not mount it yet), `<runefoble-stand-in-guardrails>` | `services/character_sheet/ui/src/*.stories.ts` |
| `game_session` | `@runefoble/game-session-ui` | `<runefoble-campaign-join>` (the join view of `#/join/:token`, ADR-0023; property `inviteToken`, `phase` (`account-form`, `account-sending`, `account-refused`, `account-accepted`, `join-ready`, `joining`, `joined`, `join-refused`), `message`, `campaignId`, `memberRole`; events `account-requested` with `{inviteToken, email, displayName}`, `join-requested` with `{inviteToken}`, `sign-in-requested`; the App Shell runs the requests), `<runefoble-initiative-tracker>`, `<runefoble-dice-roller>`, `<runefoble-spectator-view>`, `<runefoble-combat-reaction-prompt>`, `<runefoble-ready-action-card>`, `<runefoble-session-recap>` (the App Shell mounts it when the session status is `ended`; lists the chronicle lines and the dice, move and stand-in counts; TASK-0953) | `services/game_session/ui/src/*.stories.ts` |
| `the_watcher` | `@runefoble/the-watcher-ui` | `<runefoble-watcher-feed>`, `<runefoble-autonomous-dm>`, `<runefoble-dm-whisper-bar>`, `<runefoble-faction-radar>`, `<runefoble-faction-espionage>` | `services/the_watcher/ui/src/*.stories.ts` |
| `asset_forge` | `@runefoble/asset-forge-ui` | `<runefoble-asset-forge>`, `<runefoble-print-forge>` | `services/asset_forge/ui/src/*.stories.ts` |
| `voice_agent` | `@runefoble/voice-agent-ui` | `<runefoble-voice-controls>`, `<runefoble-audio-indicator>`, `<runefoble-mobile-companion>` (subviews: `<audio-stream-controller>`, `<haptic-ping-panel>`, `<connection-status-badge>`), `<runefoble-voice-duplex-controls>` | `services/voice_agent/ui/src/*.stories.ts` |
| `frontend` (App Shell) | `frontend` | `<runefoble-app>`, `<runefoble-settings-modal>`, `<runefoble-theme-switcher>` | `frontend/src/stories/runefoble-settings-modal.stories.ts` |


## Session Mesh Events

The App Shell forwards incoming session WebSocket messages to microfrontends as window events. The shell does not query service element tags or call their methods (TASK-0826, audit F-07). Each owner subscribes to the events it needs.

The gateway refuses `dice_rolled`, `turn_advanced` and `dm_whisper` from clients (TASK-0910). The gateway sends `dice_rolled` and `turn_advanced` from the game_session domain events (TASK-0923). The gateway sends `dm_whisper` from the Watcher `whisper_recorded` event, to DM sockets only (TASK-0927). `aoe_placed` and `spell_vfx` are client kinds that need `session.participate`. The gateway sends `chronicle_entry` from the game_session `token_move_chronicled` event. The shell does not forward `chronicle_entry` as a window event. It adds `entry` to the `events` property of `<runefoble-watcher-feed>`, once by `event_id`. See "Session WebSocket inbound frames" in [`ports-and-endpoints.md`](ports-and-endpoints.md).

| Session message `type` | Window event | Detail | Subscribers |
|---|---|---|---|
| `dice_rolled` | `runefoble:dice-rolled` | the session message | `<runefoble-dice-tray-3d>` (rolls the tray), `<runefoble-board>` (`roll3DDice`). The shell also adds one chronicle row (speaker `rollerName`, text `formula = total`, kind `dice_roll`) to `<runefoble-watcher-feed>`. `<runefoble-dice-roller>` does not subscribe: it sends each roll to `POST /api/v1/sessions/{session_id}/roll` and shows the reply (TASK-0951) |
| `turn_advanced` | `runefoble:turn-advanced` | the session message | `<runefoble-initiative-tracker>` (sets `activeCombatantId` and `roundNumber`, or advances the turn), `<runefoble-board>` (sets `activeTurnTokenId`) |
| `aoe_placed` | `runefoble:aoe-placed` | the session message | `<runefoble-board>` (sets `activeAoE`) |
| `spell_vfx` | `runefoble:spell-vfx` | the session message | `<runefoble-board>` (`triggerSpellVFX`) |
| `dm_whisper` | `runefoble:dm-whisper` | the session message | `<runefoble-dm-whisper-bar>` (appends to `whispers`) |

Rules:
- The shell dispatches each event on `globalThis` (the window). The event does not bubble. Elements inside plugin slot shadow roots receive it, so the events are global.
- Each subscriber adds its listener in `connectedCallback` and removes it in `disconnectedCallback`. A removed element does not react.
- A subscriber reads `event.detail` only. The payload is the session message as the server sent it.
- A message type that is not in the table is not forwarded.
- Tests: `frontend/test-dom/session-mesh-events.test.ts` sends each message through the shell and checks the mounted element.

### Shell Chrome Methods

The shell does not read the shadow root of any element that it renders (TASK-0761). It holds a Lit `ref` to its own chrome elements and calls their public methods only.

| Element | Method | The shell calls it when |
|---|---|---|
| `<runefoble-header>` | `restoreFocus()`: moves focus to the settings control | the settings modal sends `settings-closed` |

Tests: `frontend/test-dom/settings-focus-restore.test.ts` closes the modal through the shell and checks the focus.

## Auth Context Contract (`runefoble-auth`)

Microfrontends never read the shell's storage keys. The App Shell gives them the access token through the W3C Context Community Protocol (`@lit/context`).

| Item | Value |
|---|---|
| Context key | `runefoble-auth` (`AUTH_CONTEXT_KEY` in `@runefoble/ui-core`) |
| Value | `{ getAccessToken(): Promise<string \| null> }` |
| Provider | `runefoble-app` (`frontend/src/auth/auth-context-provider.ts`). It re-notifies subscribers on each sign-in change. |
| Consumer | `AuthConsumerController` from `@runefoble/ui-core`. `authHeaders()` returns `{ Authorization: 'Bearer ...' }`, or `{}` with no token. |

Rules:
- A consumer dispatches a composed, bubbling `context-request` event. The controller does this for you.
- With no provider (Storybook alone), no token is sent. The request fails with 401. The component renders the error. It never shows demo data.
- In Storybook, wrap the component in `<runefoble-story-auth-provider token="...">` (`@runefoble/ui-core/story-auth-provider`).
- Shared package: `libs/runefoble_ui` (`@runefoble/ui-core`).

## Shared HTTP and Socket Helpers (`@runefoble/ui-core`)

Source: `libs/runefoble_ui/src/http.ts` (TASK-0825, TASK-0758). Every microfrontend and the App Shell use these helpers. Do not add a local copy. The full contract is in [UI transport](ui-transport.md).

| Export | Behaviour |
|---|---|
| `request<T>(path, spec, opts)` | Sends the request and resolves with the parsed JSON. An empty success body resolves with `undefined`. A non-2xx response throws `HttpError`. |
| `postJson<T>(path, body, opts)` | `request` with `POST` and a JSON body. |
| `postForm<T>(path, form, opts)` | `request` with `POST` and a `FormData` body. |
| `opts.apiBase` | API base put in front of the path. Empty means the page origin. |
| `opts.auth` | Bearer source, such as the `AuthConsumerController`. |
| `opts.headers` | Extra headers. They win over the auth headers. |
| `opts.fetchImpl` | Transport override for tests. The default reads the global `fetch` at call time. |
| `HttpError` | `status` and `detail`. `detail` is the server `detail` (a string, or the joined FastAPI `msg` values), else the body `message`, else `Request failed with status <code>`. |
| `UnreadableResponseError` | A 2xx response whose body is not JSON. It has the `status` of that response. |
| `requestFailureMessage(err)` | The user-facing message for a failed call: `detail` for `HttpError`, the unreadable-body text for `UnreadableResponseError`, else `Network error: <reason>`. |
| `actionFailureMessage(err, action)` | The user-facing message for a failed action: a sign-in text for `401`, a not-authorized text for `403`, `Service unavailable: <detail>` for `503`, else the detail. |
| `ActionResult` | `{ ok: true } \| { ok: false; message }`. Used by writes that report and never throw. |
| `bearerHeaders(token)` | `{ Authorization: 'Bearer ...' }` for a token, else `{}`. |
| `wsUrl(path, loc?)` | `wss:` on an `https:` page, else `ws:`, on `loc.host`. Pass `{ protocol, host }` to build a URL for another origin. |
| `isRecord(value)` | Type guard for an object. |

Rules:
- A failed call throws. It never returns substitute data.
- Keep route paths and domain function names in the owning bounded context. Only the transport moves to `@runefoble/ui-core`.

## Pnpm Monorepo Workspace

The monorepo workspace links packages using standard pnpm workspace protocols:

```yaml
# pnpm-workspace.yaml
packages:
  - 'frontend'
  - 'services/*/ui'
  - 'libs/runefoble_ui'

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

Every service includes the shared router from `runefoble_platform.ui_manifest.ui_manifest_router(manifest_path, *, summary)`. No service has a local `/ui/manifest` handler. The router reads `ui/manifest.json` once, when the service builds its app, and `GET /ui/manifest` returns that parsed file unchanged. The OpenAPI spec of each service lists the operation under the `Microfrontends` tag. A missing file, an unreadable file, invalid JSON, or JSON that is not an object raises `UIManifestError` when the app is built, so the process stops at start-up. No service serves a hardcoded fallback manifest (ADR-0015 4). Run `make check-ui-manifests` to check every manifest.

Container images:
- `deployments/docker/python-service.Dockerfile` installs the service in editable mode. The module files stay under `/app/services/<bc>/src`, so `ui/manifest.json` beside `src/` resolves inside the image.
- The root `.dockerignore` excludes `services/*/ui/*` and re-includes only `services/*/ui/manifest.json`.

Components that the App Shell renders from `frontend/src` (for example `runefoble-bulletin-board`, `runefoble-merchant-haggler`, `runefoble-minigame-darts`) have no tag in any service `ui/src`. They do not appear in any manifest (ADR-0013).

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

## Component Specification: `<runefoble-mobile-companion>`

The `@runefoble/voice-agent-ui` package vendors `<runefoble-mobile-companion>` for tactile mobile participation, low-bandwidth WebRTC Opus voice streaming, haptic whisper vibration alerts, and privacy-shielded secret DM overlays.

### Properties & Attributes

| Property | Type | Default | Description |
|---|---|---|---|
| `sessionId` | `string` | `''` | Current game session identifier. |
| `userId` | `string` | `''` | Authenticated mobile player identifier. |
| `channelName` | `string` | `'Mobile Audio Companion'` | Active cellular voice room name. |
| `connected` | `boolean` | `false` | Gateway WebSocket and audio connection status. |
| `audioTier` | `'mobile_optimized' \| 'cellular_constrained' \| 'ultra_low'` | `'mobile_optimized'` | Adaptive cellular Opus streaming tier. |
| `sampleRate` | `number` | `16000` | Voice Opus sample rate in Hz. |
| `bitrateKbps` | `number` | `16` | Current streaming bitrate in kbps. |
| `bufferHealthMs` | `number` | `45` | Real-time audio buffer health in milliseconds. |
| `privacyBlur` | `boolean` | `true` | When true, obscures secret DM whispers with CSS backdrop blur. |
| `packetLoss` | `number` | `0` | Packet loss ratio (0.0 to 1.0). |
| `bandwidthKbps` | `number` | `100` | Estimated downlink bandwidth in kbps. |
| `isTransmitting` | `boolean` | `false` | Active push-to-talk transmission state. |

### Dispatched CustomEvents

| Event Name | Detail Payload | Description |
|---|---|---|
| `ptt-start` | `{ timestamp: number, channel: string }` | Dispatched when the user presses and holds the push-to-talk button. |
| `ptt-end` | `{ timestamp: number, channel: string }` | Dispatched when the push-to-talk button is released. |
| `haptic-pulse` | `{ pattern: number[], type: string }` | Dispatched whenever a tactile vibration is triggered via `navigator.vibrate`. |
| `whisper-received` | `{ whisper: WhisperMessage }` | Dispatched when a secret DM whisper frame arrives over the WebSocket. |
| `whisper-dismissed` | `{ id: string }` | Dispatched when the user dismisses the active secret whisper banner. |
| `whisper-blur-toggled` | `{ blurred: boolean }` | Dispatched when privacy blur is toggled on/off to reveal/conceal text. |
| `connection-changed` | `{ connected: boolean, sessionId: string }` | Dispatched on WebSocket connect/disconnect lifecycle changes. |

### Tactile Feedback & Privacy Controls
- **Vibration API Dispatcher**: Gracefully invokes `navigator.vibrate(pattern)` with acoustic synth fallback on non-vibrating platforms.
- **Privacy Shield**: Blurs secret text (`filter: blur(8px)`) until the user explicitly taps the reveal toggle, preventing shoulder surfing during live game sessions.
- **Buffer & Tier Monitoring**: Visual progress bar tracking buffer health around the nominal 45ms target, warning players when cellular jitter degrades transmission.

## Component Style Modularization (`*.styles.ts` Pattern)

To enforce **Hard Invariant 6** (source file length limit < 500 lines) and promote Bauhaus design token reuse, microfrontend Lit components extract extensive CSS style sheets into dedicated companion `.styles.ts` modules.

### Pattern Conventions
1. **Module Naming**: Companion styles reside adjacent to the component file (e.g. `runefoble-initiative-tracker.styles.ts` alongside `runefoble-initiative-tracker.ts`).
2. **Export Binding**: The styles file exports a `CSSResult` created via Lit's `css` template tag:
   ```typescript
   import { css } from 'lit';

   export const initiativeTrackerStyles = css`
     :host {
       display: block;
       /* ... */
     }
   `;
   ```
3. **Component Binding**: The component imports the style object and assigns it to `static styles`:
   ```typescript
   import { LitElement, html } from 'lit';
   import { customElement } from 'lit/decorators.js';
   import { initiativeTrackerStyles } from './runefoble-initiative-tracker.styles.ts';

   @customElement('runefoble-initiative-tracker')
   export class RunefobleInitiativeTracker extends LitElement {
     static styles = [initiativeTrackerStyles];
   }
   ```
4. **Contract Preservation**: Style extraction maintains 100% API contract stability (identical custom element tag name, properties, attributes, and emitted `CustomEvent` signatures).

### Sub-Stylesheet Modular Decomposition Pattern

When companion `.styles.ts` files approach modular size thresholds (> 300 lines), they are decomposed into focused single-responsibility sub-stylesheets under a `styles/` subfolder (e.g. `services/rules_compendium/ui/src/styles/`):
- `compendium-base.styles.ts`: Host container, search bar, navigation tabs, filter pills, and results cards (< 100 lines).
- `encounter-builder.styles.ts`: Difficulty meters, monster tags, party thresholds, and draft roster controls (< 120 lines).
- `homebrew-form.styles.ts`: Form inputs, stat block preview grids, and action button groups (< 110 lines).
- **Aggregator (`runefoble-rules-compendium.styles.ts`)**: Imports all sub-stylesheets and combines them into an exported `compendiumStyles: CSSResult[]` array (< 60 lines). It re-exports no sub-stylesheet. Components import `compendiumStyles` only.


