/**
 * WebSocket subprotocol contract (ADR-0015 c, TASK-0522).
 *
 * The client sends the Zitadel access token in `Sec-WebSocket-Protocol`. The token never
 * goes in the query string, because query strings reach the logs.
 */

export const RUNEFOBLE_SOCKET_PROTOCOL = 'runefoble.v1';
export const RUNEFOBLE_BEARER_PREFIX = 'runefoble.bearer.';

/** Returns the subprotocol list for a signed-in socket. Callers check for a token first. */
export function websocketProtocols(token: string): string[] {
  if (!token) throw new Error('A WebSocket needs a signed-in access token.');
  return [RUNEFOBLE_SOCKET_PROTOCOL, `${RUNEFOBLE_BEARER_PREFIX}${token}`];
}
