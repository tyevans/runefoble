/**
 * TASK-0757: the shell answers the `runefoble-auth` context request with the live access token.
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { AuthConsumerController } from '@runefoble/ui-core';
import { AuthContextProviderController, type AccessTokenSource } from '../src/auth/auth-context-provider.ts';

/** A minimal element: an EventTarget whose events also reach its parent, like bubbling. */
class FakeElement extends EventTarget {
  isConnected = true;
  readonly parent?: FakeElement;
  controllers: Array<{ hostConnected?: () => void; hostDisconnected?: () => void }> = [];
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

function fakeSource(initial: string | null) {
  let token = initial;
  const listeners = new Set<() => void>();
  const source: AccessTokenSource = {
    getAccessToken: () => token,
    onAuthChanged: (l) => { listeners.add(l); return () => { listeners.delete(l); }; },
  };
  return { source, signIn(t: string | null) { token = t; listeners.forEach((l) => l()); } };
}

describe('AuthContextProviderController', () => {
  it('gives a nested microfrontend the shell token as a Bearer header', async () => {
    const shell = new FakeElement();
    const { source } = fakeSource('shell-token');
    new AuthContextProviderController(shell as never, source);
    shell.connect();
    const mfe = new FakeElement(shell);
    const auth = new AuthConsumerController(mfe as never);
    mfe.connect();
    assert.deepEqual(await auth.authHeaders(), { Authorization: 'Bearer shell-token' });
  });

  it('re-notifies a subscribed microfrontend when the sign-in changes', async () => {
    const shell = new FakeElement();
    const fake = fakeSource(null);
    new AuthContextProviderController(shell as never, fake.source);
    shell.connect();
    const mfe = new FakeElement(shell);
    const auth = new AuthConsumerController(mfe as never);
    mfe.connect();
    assert.deepEqual(await auth.authHeaders(), {});
    fake.signIn('after-login');
    assert.deepEqual(await auth.authHeaders(), { Authorization: 'Bearer after-login' });
  });

  it('stops listening when the shell disconnects', () => {
    const shell = new FakeElement();
    let listening = 0;
    const source: AccessTokenSource = {
      getAccessToken: () => null,
      onAuthChanged: () => { listening++; return () => { listening--; }; },
    };
    new AuthContextProviderController(shell as never, source);
    shell.connect();
    assert.equal(listening, 1);
    shell.controllers.forEach((c) => c.hostDisconnected?.());
    assert.equal(listening, 0);
  });
});
