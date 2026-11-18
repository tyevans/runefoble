/**
 * App Shell auth context provider (TASK-0757).
 *
 * Answers `context-request` events for the `runefoble-auth` context. Microfrontends read the
 * access token through this contract. They never read the shell's storage keys.
 */

import { ContextProvider } from '@lit/context';
import type { ReactiveController, ReactiveControllerHost } from 'lit';
import { authContext, type AuthContextValue } from '@runefoble/ui-core';

/** The part of the auth service that the provider needs. */
export interface AccessTokenSource {
  getAccessToken(): string | null;
  onAuthChanged(listener: () => void): () => void;
}

type ProviderHost = ReactiveControllerHost & HTMLElement;

export class AuthContextProviderController implements ReactiveController {
  private readonly provider: ContextProvider<typeof authContext>;
  private readonly source: AccessTokenSource;
  private unlisten: (() => void) | null = null;

  constructor(host: ProviderHost, source: AccessTokenSource) {
    this.source = source;
    this.provider = new ContextProvider(host, { context: authContext, initialValue: this.snapshot() });
    host.addController(this);
  }

  /** A new object on each sign-in change, so subscribed microfrontends are notified. */
  private snapshot(): AuthContextValue {
    return { getAccessToken: async () => this.source.getAccessToken() };
  }

  hostConnected(): void {
    this.unlisten ??= this.source.onAuthChanged(() => this.provider.setValue(this.snapshot()));
  }

  hostDisconnected(): void {
    this.unlisten?.();
    this.unlisten = null;
  }
}
