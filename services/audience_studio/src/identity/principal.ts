/**
 * Request-level access to the verified principal. The identity hook sets it before any handler runs.
 */

import type { FastifyRequest } from 'fastify';
import type { VerifiedPrincipal } from './zitadelVerifier.js';

declare module 'fastify' {
  interface FastifyRequest {
    principal?: VerifiedPrincipal;
  }
}

/**
 * Returns the principal of a request that passed the identity hook.
 * A missing principal on a protected route is a wiring defect, so it throws (500), not 401.
 */
export function principalOf(request: FastifyRequest): VerifiedPrincipal {
  if (!request.principal) {
    throw new Error(`No verified principal on ${request.method} ${request.url}`);
  }
  return request.principal;
}
