/**
 * Fastify REST routes for Audience Studio.
 * Governed by ADR-0001, ADR-0006, and Hard Invariant 5 (OpenAPI specs).
 *
 * One error handler maps typed errors to their status codes for every route in this plugin.
 * Other errors, such as schema validation failures, go to the Fastify default handler.
 */

import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ApprovalQueue } from '../approvalQueue.js';
import { ConflictError, HttpError } from '../errors.js';
import { ConcurrencyConflictError } from '../eventStore/types.js';
import type { PollEngine } from '../pollEngine.js';
import { registerPollRoutes } from './polls.js';
import { registerProposalRoutes } from './proposals.js';

export interface RouteContext {
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
}

/** A lost write race is a 409 for the client. The stream id stays out of the response. */
function toHttpError(err: unknown): HttpError | undefined {
  if (err instanceof HttpError) return err;
  if (err instanceof ConcurrencyConflictError) {
    return new ConflictError('The poll or proposal changed while the command ran. Retry the command.', {
      cause: err,
    });
  }
  return undefined;
}

export function createAudienceRoutes(ctx: RouteContext): FastifyPluginAsync {
  return async function audienceRoutes(fastify: FastifyInstance) {
    fastify.setErrorHandler((err, _request, reply) => {
      const httpError = toHttpError(err);
      if (!httpError) {
        throw err;
      }
      return reply.code(httpError.statusCode).send({ error: httpError.message });
    });
    registerPollRoutes(fastify, ctx.pollEngine);
    registerProposalRoutes(fastify, ctx.approvalQueue);
  };
}
