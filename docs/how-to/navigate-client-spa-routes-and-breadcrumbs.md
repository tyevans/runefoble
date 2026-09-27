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

Register route guards with `router.beforeEach()` to intercept navigation before view transitions occur. Guards can return:
- `true`: Allow navigation.
- `false`: Abort navigation and stay on the current route.
- A `string`: Redirect navigation to another route (e.g. `#/login`).

```typescript
import { router } from './router/index.ts';

router.beforeEach((to, from) => {
  const token = localStorage.getItem('runefoble-token');
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

Provide custom title resolvers to replace numeric IDs with narrative campaign or session names:

```typescript
import { router } from './router/index.ts';

router.setTitleResolver((type, id) => {
  if (type === 'campaign' && id === '4') {
    return 'Tomb of the Star-Eater';
  }
  if (type === 'session' && id === '14') {
    return 'Session #14 (Crypt Entrance)';
  }
  return undefined;
});
```
