# How to Navigate Client-Side SPA Routes and Breadcrumbs

This practical recipe demonstrates how to utilize Runefoble's lightweight client-side SPA router (`Router`) and dynamic breadcrumb navigation component (`<runefoble-breadcrumbs>`) in the frontend application shell.

## Prerequisites

- Frontend workspace initialized (`pnpm install`).
- Basic familiarity with Lit Web Components and hash-based client routing.

## 1. Supported Route Patterns

The client router (`frontend/src/router/router.ts`) supports standard deep-linkable URLs with parameterized segments:

| Route Pattern | Description | Example URL |
|---|---|---|
| `#/login` | User login and authentication | `http://localhost/#/login` |
| `#/register` | User account registration | `http://localhost/#/register` |
| `#/campaigns` | Campaign management hub / dashboard | `http://localhost/#/campaigns` |
| `#/campaigns/:campaignId` | Campaign details & membership | `http://localhost/#/campaigns/4` |
| `#/campaigns/:campaignId/characters` | Campaign party roster | `http://localhost/#/campaigns/4/characters` |
| `#/campaigns/:campaignId/lobby/:sessionId` | Pre-game assembly lobby | `http://localhost/#/campaigns/4/lobby/15` |
| `#/campaigns/:campaignId/sessions/:sessionId` | Active live VTT session | `http://localhost/#/campaigns/4/sessions/14` |
| `#/characters` | Personal character roster | `http://localhost/#/characters` |
| `#/characters/:characterId` | Character Sheet inspector & inventory | `http://localhost/#/characters/char-valeros` |
| `#/profile` | User profile & security settings | `http://localhost/#/profile` |

## 2. Navigating Programmatically

Import the router singleton instance and invoke `navigate()`:

```typescript
import { router } from './router/index.ts';

// Navigate to active session
await router.navigate('#/campaigns/4/sessions/14');

// Navigate with query parameters
await router.navigate('#/campaigns?filter=active&sort=recent');
```

## 3. Configuring Authentication Route Guards

Register route guards with `registerAuthGuard(router, authService)` or manually via `router.beforeEach()` to intercept navigation before view transitions occur. Guards can return:
- `true`: Allow navigation.
- `false`: Abort navigation and stay on the current route.
- A `string`: Redirect navigation to another route (e.g. `#/login`).

### Using `registerAuthGuard` (Recommended)

The `registerAuthGuard` utility registers a `beforeEach` navigation guard and listens for auth session changes (such as logout or token expiry) to automatically redirect protected routes to `#/login`:

```typescript
import { router, registerAuthGuard } from './router/index.ts';
import { authService } from './auth/auth-service.ts';

// Register auth guard with default public routes (['#/login', '#/register'])
const unregisterGuard = registerAuthGuard(router, authService);

// Unregister when tearing down component
unregisterGuard();
```

### Custom `beforeEach` Route Guards

```typescript
import { router } from './router/index.ts';

router.beforeEach((to, from) => {
  const token = localStorage.getItem('rf_auth_session');
  const isPublic = to.path === '#/login' || to.path === '#/register';

  if (!token && !isPublic) {
    // Redirect unauthenticated visitor to login
    return '#/login';
  }
  return true;
});
```

## 4. Managing Route Lifecycle Teardown

To prevent memory leaks, lingering WebSockets, or active WebAudio contexts during long sessions, register teardown handlers:

```typescript
import { router } from './router/index.ts';

// When entering a session route
const unregisterTeardown = router.registerTeardown(async () => {
  // Cleanly close session WebSocket
  if (sessionSocket) {
    sessionSocket.close();
  }
  // Halt active audio streams and visualizer frames
  audioContext.suspend();
});
```

When `router.navigate()` is triggered, all registered teardown handlers from the current route execute before transitioning to the target view.

## 5. Rendering Dynamic Breadcrumbs

Use the `<runefoble-breadcrumbs>` Lit component in your header or navigation chrome:

```html
<runefoble-breadcrumbs
  .items=${[
    { label: 'Campaigns', path: '#/campaigns' },
    { label: 'Tomb of the Star-Eater', path: '#/campaigns/4' },
    { label: 'Session #14', path: '#/campaigns/4/sessions/14', active: true }
  ]}
  separator="›"
  @breadcrumb-click=${(e) => console.log('Navigated to:', e.detail.path)}
></runefoble-breadcrumbs>
```

Alternatively, enable `autoRouter` to have the breadcrumbs component automatically subscribe to router changes:

```html
<runefoble-breadcrumbs autoRouter></runefoble-breadcrumbs>
```

## 6. Resolving Custom Entity Titles in Breadcrumbs

Provide custom title resolvers to replace numeric IDs with narrative campaign or session names. The router supports both synchronous fallback resolvers and asynchronous resolvers with built-in title caching.

### Synchronous Resolvers (`setTitleResolver`)

```typescript
import { router } from './router/index.ts';

router.setTitleResolver((type, id) => {
  if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
  if (type === 'campaign' && id === '5') return 'Whispering Depths';
  if (type === 'session' && id === '14') return 'Session #14 (Crypt Entrance)';
  return undefined;
});
```

### Asynchronous Dynamic Resolvers with Caching (`setAsyncTitleResolver`)

For dynamically created campaigns and sessions loaded from the backend API, register an asynchronous resolver via `router.setAsyncTitleResolver()`. Resolved titles are automatically cached in `router` so subsequent navigation or breadcrumb renders do not trigger redundant network requests or flash raw identifiers:

```typescript
import { router } from './router/index.ts';
import { appDataService } from './services/app-data-service.ts';

router.setAsyncTitleResolver(async (type, id) => {
  if (type === 'campaign') {
    const campaign = await appDataService.fetchCampaign(id);
    return campaign?.title;
  }
  if (type === 'character') {
    const character = await appDataService.fetchCharacter(id);
    return character?.name;
  }
  if (type === 'session' || type === 'lobby') {
    const session = await appDataService.fetchSession(id);
    return session?.title;
  }
  return undefined;
});
```

When navigating to deep routes (e.g., `#/campaigns/camp-1790564858218` or `#/characters/char-valeros`), `router.navigate()` awaits title resolution before emitting `route-changed` and updating breadcrumb labels (`Home > Characters > Valeros of Korvosa`).

## 7. Vite Development API & WebSocket Proxying

In local development (`http://localhost:5173`), Vite proxies REST API and WebSocket connections to the Gateway API server (`http://localhost:8000`) in `frontend/vite.config.ts`:

- `/api/v1` &rarr; `http://localhost:8000` (with `changeOrigin: true`)
- `/ws` &rarr; `ws://localhost:8000` (with `ws: true`)

The proxy target defaults to `http://localhost:8000` and can be overridden via the `GATEWAY_API_URL` environment variable:

```bash
GATEWAY_API_URL=http://localhost:8000 pnpm dev
```

## 8. Auditing Route Declarations and Breadcrumbs

To verify that all registered standard routes parse parameters, resolve titles, and mount views without collision, run the automated audit test suites:

```bash
# Frontend component and route matrix audit
node --experimental-strip-types --test frontend/test/app-shell-views-wiring-audit.test.ts

# Modular App Shell test submodules (routing, session transitions, websocket lifecycle, breadcrumbs)
node --experimental-strip-types --test frontend/test/app_shell/*.test.ts

# Python blackbox frontdoor E2E test suites
uv run pytest tests/test_blackbox_app_shell_views_audit.py tests/test_blackbox_app_shell_test_modular_decomposition.py
```

## 9. Modular Data Service & Offline Fixture Fallbacks

To preserve Hard Invariant 6 (<500 lines) and separate network transport from test fixture data, `AppDataService` delegates static campaign, character, and session fixtures to `frontend/src/services/app-data-service.fixtures.ts`:

- `FALLBACK_CAMPAIGNS`: Default campaign items (`Tomb of the Star-Eater`, `Whispering Depths`).
- `FALLBACK_CHARACTERS`: Default character roster items (`Valeros`, `Kyra`, `Ezren`).
- `FALLBACK_MEMBERS`: Default campaign party members.
- `FALLBACK_PARTICIPANTS`: Pre-game lobby attendee states.
- `FALLBACK_SESSIONS`: Staged and active campaign sessions.

When backend services are unavailable during offline development or isolated unit testing, `appDataService` gracefully falls back to these static fixtures without crashing.


