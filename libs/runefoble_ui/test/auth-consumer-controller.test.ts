import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { ContextProvider } from '@lit/context';
import { authContext, AuthConsumerController } from '../src/index.ts';

/** A minimal element: an EventTarget whose events also reach its parent, like bubbling. */
class FakeElement extends EventTarget {
  isConnected = true;
  controllers: Array<{ hostConnected?: () => void }> = [];
  readonly parent?: FakeElement;
  constructor(parent?: FakeElement) { super(); this.parent = parent; }
  addController(c: { hostConnected?: () => void }) { this.controllers.push(c); }
  removeController() {}
  requestUpdate() {}
  get updateComplete() { return Promise.resolve(true); }
  override dispatchEvent(event: Event): boolean {
    super.dispatchEvent(event);
    this.parent?.dispatchEvent(event);
    return true;
  }
  connect() { this.controllers.forEach((c) => c.hostConnected?.()); }
}

function mount(token: string | null | 'no-provider') {
  const root = new FakeElement();
  const child = new FakeElement(root);
  let provider: ContextProvider<typeof authContext> | undefined;
  if (token !== 'no-provider') {
    provider = new ContextProvider(root as never, {
      context: authContext,
      initialValue: { getAccessToken: async () => token },
    });
    root.connect();
  }
  const controller = new AuthConsumerController(child as never);
  child.connect();
  return { controller, provider };
}

describe('AuthConsumerController', () => {
  it('sends a Bearer header when the shell provides a token', async () => {
    const { controller } = mount('tok-123');
    assert.deepEqual(await controller.authHeaders(), { Authorization: 'Bearer tok-123' });
  });

  it('sends no header when the shell is signed out', async () => {
    const { controller } = mount(null);
    assert.deepEqual(await controller.authHeaders(), {});
  });

  it('sends no header when there is no provider', async () => {
    const { controller } = mount('no-provider');
    assert.equal(await controller.getAccessToken(), null);
  });

  it('follows the provider when the shell re-notifies', async () => {
    const { controller, provider } = mount('old');
    provider!.setValue({ getAccessToken: async () => 'new' });
    assert.equal(await controller.getAccessToken(), 'new');
  });
});
