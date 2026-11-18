/**
 * Fastify REST routes for Audience Studio.
 * Governed by ADR-0001, ADR-0006, and Hard Invariant 5 (OpenAPI specs).
 */

import type { FastifyInstance, FastifyPluginAsync, FastifyReply } from 'fastify';
import type { ApprovalQueue } from './approvalQueue.js';
import { DependencyUnavailableError, DomainError } from './errors.js';
import { principalOf } from './identity/principal.js';
import type { PollEngine } from './pollEngine.js';
import type { ProposalStatus } from './types.js';

interface RouteContext {
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
}

/** Maps domain and dependency errors to HTTP status codes. Other errors reach Fastify as 500. */
function sendError(reply: FastifyReply, err: unknown) {
  if (err instanceof DomainError) {
    return reply.code(err.statusCode).send({ error: err.message });
  }
  if (err instanceof DependencyUnavailableError) {
    return reply.code(503).send({ error: err.message });
  }
  throw err;
}

export function createAudienceRoutes(ctx: RouteContext): FastifyPluginAsync {
  return async function audienceRoutes(fastify: FastifyInstance) {
    // 1. Create a new audience poll
    fastify.post<{
      Body: {
        campaign_id: string;
        session_id?: string;
        title: string;
        prompt: string;
        options: string[];
        duration_seconds?: number;
        quorum?: number;
        modifier_type?: string;
      };
    }>('/polls', {
      schema: {
        description: 'Create a live audience chaos poll',
        tags: ['Audience'],
        body: {
          type: 'object',
          required: ['campaign_id', 'title', 'prompt', 'options'],
          properties: {
            campaign_id: { type: 'string' },
            session_id: { type: 'string' },
            title: { type: 'string' },
            prompt: { type: 'string' },
            options: { type: 'array', items: { type: 'string' } },
            duration_seconds: { type: 'integer' },
            quorum: { type: 'integer' },
            modifier_type: { type: 'string' },
          },
        },
      },
    }, async (request, reply) => {
      const b = request.body;
      try {
        const poll = await ctx.pollEngine.createPoll({
          campaignId: b.campaign_id,
          sessionId: b.session_id,
          title: b.title,
          prompt: b.prompt,
          options: b.options,
          durationSeconds: b.duration_seconds,
          quorum: b.quorum,
          modifierType: b.modifier_type,
        });
        return reply.code(201).send(poll);
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 2. List audience polls
    fastify.get<{ Querystring: { campaign_id?: string } }>('/polls', {
      schema: {
        description: 'List active and past audience polls',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const polls = await ctx.pollEngine.listPolls(request.query.campaign_id);
        return reply.send({ polls });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 3. Get single poll details
    fastify.get<{ Params: { pollId: string } }>('/polls/:pollId', {
      schema: {
        description: 'Get details and live results of an audience poll',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const poll = await ctx.pollEngine.getPoll(request.params.pollId);
        if (!poll) {
          return reply.code(404).send({ error: 'Poll not found' });
        }
        return reply.send(poll);
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 4. Cast a spectator vote
    fastify.post<{
      Params: { pollId: string };
      Body: { option_id: string; channel?: string };
    }>('/polls/:pollId/votes', {
      schema: {
        description: 'Cast an audience spectator vote. The voter is the token subject.',
        tags: ['Audience'],
        body: {
          type: 'object',
          required: ['option_id'],
          properties: {
            option_id: { type: 'string' },
            channel: { type: 'string' },
          },
        },
      },
    }, async (request, reply) => {
      const { pollId } = request.params;
      const { option_id, channel } = request.body;
      try {
        const poll = await ctx.pollEngine.castVote(
          pollId,
          principalOf(request).userId,
          option_id,
          channel ?? 'web'
        );
        return reply.send({ success: true, poll });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 5. Close a poll and trigger quorum aggregation
    fastify.post<{ Params: { pollId: string } }>('/polls/:pollId/close', {
      schema: {
        description: 'Close poll and resolve modifier proposals',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const poll = await ctx.pollEngine.closePoll(request.params.pollId);
        return reply.send(poll);
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 6. List pending modifier proposals
    fastify.get<{
      Querystring: { campaign_id?: string; status?: ProposalStatus };
    }>('/proposals', {
      schema: {
        description: 'List modifier proposals in DM approval queue',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposals = await ctx.approvalQueue.getProposals(
          request.query.campaign_id,
          request.query.status
        );
        return reply.send({ proposals });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 7. Approve modifier proposal (DM Zanzibar authorized)
    fastify.post<{ Params: { proposalId: string } }>('/proposals/:proposalId/approve', {
      schema: {
        description: 'Approve chaos modifier proposal. The actor is the token subject, checked against SpiceDB.',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposal = await ctx.approvalQueue.approveProposal(
          request.params.proposalId,
          principalOf(request).userId
        );
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 8. Veto modifier proposal (DM Zanzibar authorized)
    fastify.post<{ Params: { proposalId: string } }>('/proposals/:proposalId/veto', {
      schema: {
        description: 'Veto chaos modifier proposal. The actor is the token subject, checked against SpiceDB.',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposal = await ctx.approvalQueue.vetoProposal(
          request.params.proposalId,
          principalOf(request).userId
        );
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });
  };
}
