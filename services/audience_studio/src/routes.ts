/**
 * Fastify REST routes for Audience Studio.
 * Governed by ADR-0001, ADR-0006, and Hard Invariant 5 (OpenAPI specs).
 */

import type { FastifyInstance, FastifyPluginAsync, FastifyReply } from 'fastify';
import type { ApprovalQueue } from './approvalQueue.js';
import { HttpError } from './errors.js';
import { principalOf } from './identity/principal.js';
import type { PollEngine } from './pollEngine.js';
import type { ProposalStatus } from './types.js';

interface RouteContext {
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
}

/** Maps typed HTTP errors to their status codes. Other errors reach Fastify as 500. */
function sendError(reply: FastifyReply, err: unknown) {
  if (err instanceof HttpError) {
    return reply.code(err.statusCode).send({ error: err.message });
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
        description: 'Create a live audience chaos poll. The actor needs run_session on the campaign.',
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
        const poll = await ctx.pollEngine.createPoll(principalOf(request), {
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
        description: 'List audience polls the caller can view (audience_poll.view).',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const polls = await ctx.pollEngine.listPolls(principalOf(request), request.query.campaign_id);
        return reply.send({ polls });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 3. Get single poll details
    fastify.get<{ Params: { pollId: string } }>('/polls/:pollId', {
      schema: {
        description: 'Get details and live results of an audience poll (audience_poll.view).',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        return reply.send(await ctx.pollEngine.getPoll(request.params.pollId, principalOf(request)));
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
        description: 'Cast an audience vote (audience_poll.vote). The voter is the token subject.',
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
        const poll = await ctx.pollEngine.castVote(pollId, principalOf(request), option_id, channel ?? 'web');
        return reply.send({ success: true, poll });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 5. Close a poll and trigger quorum aggregation
    fastify.post<{ Params: { pollId: string } }>('/polls/:pollId/close', {
      schema: {
        description: 'Close poll and resolve modifier proposals (audience_poll.moderate).',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const poll = await ctx.pollEngine.closePoll(request.params.pollId, principalOf(request));
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
        description: 'List modifier proposals the caller can view. Parameters appear only with audience_poll.approve.',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposals = await ctx.approvalQueue.getProposals(
          principalOf(request),
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
        description: 'Approve chaos modifier proposal (audience_poll.approve). The actor is the token subject.',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposal = await ctx.approvalQueue.approveProposal(request.params.proposalId, principalOf(request));
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });

    // 8. Veto modifier proposal (DM Zanzibar authorized)
    fastify.post<{ Params: { proposalId: string } }>('/proposals/:proposalId/veto', {
      schema: {
        description: 'Veto chaos modifier proposal (audience_poll.veto). The actor is the token subject.',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      try {
        const proposal = await ctx.approvalQueue.vetoProposal(request.params.proposalId, principalOf(request));
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        return sendError(reply, err);
      }
    });
  };
}
