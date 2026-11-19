# How-To: Authoring Service Microfrontends

This guide walks through creating or extending a frontend microfrontend component within a service bounded context (`services/<bc>/ui/`).

## Step 1: Create the Component in the Service Bounded Context

Create your Lit custom element in `services/<service_name>/ui/src/<component-name>.ts`:

```typescript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-my-feature')
export class RunefobleMyFeature extends LitElement {
  @property({ type: String }) title = 'Feature';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, sans-serif);
      color: var(--rf-text-primary, #121212);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
      box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
      padding: 16px;
    }
  `;

  render() {
    return html`<div><h3>${this.title}</h3></div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-my-feature': RunefobleMyFeature;
  }
}
```

## Step 2: Export Component from the Package Index

Add the component to `services/<service_name>/ui/src/index.ts`:

```typescript
export * from './runefoble-my-feature.ts';
```

## Step 3: Add an Interactive Story in the Service UI

Create `services/<service_name>/ui/src/<component-name>.stories.ts` following Hard Invariant 3:

```typescript
import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-my-feature.ts';

const meta: Meta = {
  title: 'Feature/RunefobleMyFeature',
  component: 'runefoble-my-feature',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => html`<runefoble-my-feature title="Sample Feature"></runefoble-my-feature>`,
};
```

## Step 4: Register in Service Frontdoor Manifest

In `services/<service_name>/src/<service_name>/main.py`, include the custom element in the `/ui/manifest` endpoint:

```python
@app.get("/ui/manifest")
def get_ui_manifest():
    return {
        "service": "<service_name>",
        "package": "@runefoble/<service_name>-ui",
        "components": ["runefoble-my-feature"],
        "version": "0.1.0",
    }
```

## Step 5: Verify in Storybook & Build

Run the developer Storybook target to inspect your component in isolation:

```bash
make dev-storybook
```

Verify that the TypeScript build and test suite pass cleanly:

```bash
make test
make lint
```

## Step 6: Call Authenticated APIs With the Auth Context

Do not read tokens from `localStorage`. Ask the App Shell through the auth context.

1. Add `"@runefoble/ui-core": "workspace:*"` to the UI package dependencies.
2. Create the controller in the component:

```ts
import { AuthConsumerController, HttpError, request } from '@runefoble/ui-core';

private readonly auth = new AuthConsumerController(this);

try {
  const data = await request<Result>(path, {}, { apiBase: this.apiBaseUrl, auth: this.auth });
  this.result = data;
} catch (err) {
  this.error = err instanceof HttpError ? `Request failed (status ${err.status}).` : 'The request failed.';
}
```

3. Catch failures and set an error state. Render the error. Do not show demo data.

For a POST with a JSON body, call `postJson(path, body, { apiBase, auth })`. For an upload, call `postForm(path, formData, { apiBase, auth })`. All helpers throw `HttpError` on a non-2xx response. `HttpError.detail` holds the server message. Do not write a local `fetch` and error parser. See [UI transport](../reference/ui-transport.md).
4. In stories, add one story with `<runefoble-story-auth-provider token="story-token">` and one story with no provider. Use `installTokenCheckingFetch` from `@runefoble/ui-core/story-fetch` to stand in for the gateway.

### WebSockets

Open a socket only with a token. Use the shared subprotocol helper. Never put the token in the URL.

```ts
import { AuthConsumerController, websocketProtocols } from '@runefoble/ui-core';

private readonly auth = new AuthConsumerController(this);

const token = await this.auth.getAccessToken();
if (!token) {
  this.socketError = 'Sign in to open the live connection.';
  return;
}
this.ws = new WebSocket(wsUrl('/ws/your-route/' + id), websocketProtocols(token));
```

`wsUrl(path)` builds the `ws:` or `wss:` URL on the page origin. Do not write the protocol ternary by hand.

`websocketProtocols` returns `['runefoble.v1', 'runefoble.bearer.<token>']`. The gateway closes a refused handshake with code 1008. Set an error state on code 1008 and render it. The App Shell clears the session and sends the user to sign-in.

### Shared token helper

Each package sends its own calls. The token comes from one place only:

| Where | Helper | Use |
|---|---|---|
| Microfrontend (`services/<bc>/ui`) | `AuthConsumerController` (`authHeaders()`, `getAccessToken()`) and `websocketProtocols(token)` from `@runefoble/ui-core` | Calls and sockets |
| App Shell (`frontend/src`) | `authHeaders()` and `wsProtocols()` in `frontend/src/auth/transport.ts` | Shell calls and sockets |

Do not copy token logic into a package. Do not read `localStorage` for a token. Do not send an identity header such as `X-User-Id`. The server reads identity from the verified token only.

See `docs/reference/microfrontend-architecture.md` for the contract.
