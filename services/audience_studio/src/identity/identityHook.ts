/**
 * Fastify hook that verifies the caller on every route except the public operational paths.
 * Governed by ADR-0015 decision (c) and docs/how-to/verify-identity-in-fastapi-and-websockets.md.
 *
 * HTTP: `Authorization: Bearer <jwt>`.
 * WebSocket: `Sec-WebSocket-Protocol: runefoble.v1, runefoble.bearer.<jwt>`. The hook runs before
 * the handshake, so a refused upgrade never reaches the socket handler.
 */

import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { DependencyUnavailableError } from '../errors.js';
import { ZitadelVerifier, TokenRejectedError } from './zitadelVerifier.js';

/** Kubernetes probes and the microfrontend manifest carry no identity. */
export const PUBLIC_PATHS: ReadonlySet<string> = new Set(['/healthz', '/readyz', '/ui/manifest']);

export const BEARER_SUBPROTOCOL_PREFIX = 'runefoble.bearer.';

/** Extracts the token from an `Authorization: Bearer` header. */
export function bearerToken(header: string | undefined): string | undefined {
  const match = /^Bearer\s+(\S+)$/i.exec(header ?? '');
  return match?.[1];
}

/** Extracts the token from the `runefoble.bearer.<jwt>` subprotocol offered in a handshake. */
export function subprotocolToken(header: string | undefined): string | undefined {
  for (const raw of (header ?? '').split(',')) {
    const protocol = raw.trim();
    if (protocol.startsWith(BEARER_SUBPROTOCOL_PREFIX) && protocol.length > BEARER_SUBPROTOCOL_PREFIX.length) {
      return protocol.slice(BEARER_SUBPROTOCOL_PREFIX.length);
    }
  }
  return undefined;
}

function isWebSocketUpgrade(request: FastifyRequest): boolean {
  return request.headers.upgrade?.toLowerCase() === 'websocket';
}

function deny(request: FastifyRequest, reply: FastifyReply, message: string) {
  reply.code(401).header('WWW-Authenticate', 'Bearer');
  if (isWebSocketUpgrade(request)) {
    // A refused upgrade leaves the socket outside the HTTP parser, so the server never sees the client close.
    const socket = request.raw.socket;
    reply.raw.once('finish', () => socket.destroy());
  }
  return reply.send({ error: 'unauthorized', message });
}

/** Registers the verifying hook. Call before any route is registered. */
export function registerIdentityHook(server: FastifyInstance, verifier: ZitadelVerifier): void {
  server.addHook('onRequest', async (request, reply) => {
    // CORS preflight carries no credentials. The CORS plugin answers it.
    if (request.method === 'OPTIONS') return;
    const path = request.url.split('?')[0];
    if (PUBLIC_PATHS.has(path)) return;

    const token = isWebSocketUpgrade(request)
      ? subprotocolToken(request.headers['sec-websocket-protocol'])
      : bearerToken(request.headers.authorization);
    if (!token) {
      return deny(request, reply, 'A verified token is required');
    }

    try {
      request.principal = await verifier.verify(token);
    } catch (err) {
      if (err instanceof TokenRejectedError) {
        request.log.warn({ path, reason: err.message }, 'Token rejected');
        return deny(request, reply, 'Token verification failed');
      }
      if (err instanceof DependencyUnavailableError) {
        request.log.error({ err, path }, 'Identity keys unavailable');
        return reply.code(503).send({ error: err.message });
      }
      throw err;
    }
  });
}
