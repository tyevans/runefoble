/**
 * App Shell transport helper (TASK-0538).
 *
 * The one place where the App Shell turns the signed-in token into request headers and
 * WebSocket subprotocols. Every shell fetch and socket uses it. Microfrontends use the
 * same contract through `@runefoble/ui-core`.
 */

import { websocketProtocols } from '@runefoble/ui-core';
import { authService } from './auth-service.ts';

/** The part of the auth service that the transport needs. */
export interface TokenSource {
  getAccessToken(): string | null;
}

/** Returns `{ Authorization: 'Bearer ...' }` for a signed-in user, else an empty object. */
export function authHeaders(source: TokenSource = authService): Record<string, string> {
  const token = source.getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Returns the subprotocols for a socket, or null when nobody is signed in. The caller must not open the socket on null. */
export function wsProtocols(source: TokenSource = authService): string[] | null {
  const token = source.getAccessToken();
  return token ? websocketProtocols(token) : null;
}
