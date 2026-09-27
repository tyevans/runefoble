/**
 * Fastify REST routes for Audience Studio.
 * Governed by ADR-0001, ADR-0006, and Hard Invariant 5 (OpenAPI specs).
 */

import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ApprovalQueue } from './approvalQueue.js';
import type { ZanzibarClient } from './auth.js';
import type { PollEngine } from './pollEngine.js';
import type { ProposalStatus } from './types.js';

interface RouteContext {
  pollEngine: PollEngine;
  approvalQueue: ApprovalQueue;
  auth: ZanzibarClient;
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
    });

    // 2. List audience polls
    fastify.get<{ Querystring: { campaign_id?: string } }>('/polls', {
      schema: {
        description: 'List active and past audience polls',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      const polls = ctx.pollEngine.listPolls(request.query.campaign_id);
      return reply.send({ polls });
    });

    // 3. Get single poll details
    fastify.get<{ Params: { pollId: string } }>('/polls/:pollId', {
      schema: {
        description: 'Get details and live results of an audience poll',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      const poll = ctx.pollEngine.getPoll(request.params.pollId);
      if (!poll) {
        return reply.code(404).send({ error: 'Poll not found' });
      }
      return reply.send(poll);
    });

    // 4. Cast a spectator vote
    fastify.post<{
      Params: { pollId: string };
      Body: { voter_id: string; option_id: string; channel?: string };
    }>('/polls/:pollId/votes', {
      schema: {
        description: 'Cast an audience spectator vote',
        tags: ['Audience'],
        body: {
          type: 'object',
          required: ['voter_id', 'option_id'],
          properties: {
            voter_id: { type: 'string' },
            option_id: { type: 'string' },
            channel: { type: 'string' },
          },
        },
      },
    }, async (request, reply) => {
      const { pollId } = request.params;
      const { voter_id, option_id, channel } = request.body;
      try {
        const poll = await ctx.pollEngine.castVote(
          pollId,
          voter_id,
          option_id,
          channel ?? 'web'
        );
        return reply.send({ success: true, poll });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return reply.code(400).send({ error: msg });
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
        const msg = err instanceof Error ? err.message : String(err);
        return reply.code(400).send({ error: msg });
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
      const proposals = ctx.approvalQueue.getProposals(
        request.query.campaign_id,
        request.query.status
      );
      return reply.send({ proposals });
    });

    // 7. Approve modifier proposal (DM Zanzibar authorized)
    fastify.post<{
      Params: { proposalId: string };
      Body: { dm_user_id?: string };
    }>('/proposals/:proposalId/approve', {
      schema: {
        description: 'Approve chaos modifier proposal (DM authorized)',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      const dmId =
        request.body?.dm_user_id ||
        (request.headers['x-user-id'] as string) ||
        'dm-user';
      try {
        const proposal = await ctx.approvalQueue.approveProposal(
          request.params.proposalId,
          dmId
        );
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        const code = msg.includes('dungeon_master') ? 403 : 400;
        return reply.code(code).send({ error: msg });
      }
    });

    // 8. Veto modifier proposal (DM Zanzibar authorized)
    fastify.post<{
      Params: { proposalId: string };
      Body: { dm_user_id?: string };
    }>('/proposals/:proposalId/veto', {
      schema: {
        description: 'Veto chaos modifier proposal (DM authorized)',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      const dmId =
        request.body?.dm_user_id ||
        (request.headers['x-user-id'] as string) ||
        'dm-user';
      try {
        const proposal = await ctx.approvalQueue.vetoProposal(
          request.params.proposalId,
          dmId
        );
        return reply.send({ success: true, proposal });
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        const code = msg.includes('dungeon_master') ? 403 : 400;
        return reply.code(code).send({ error: msg });
      }
    });

    // 9. Sync Zanzibar relationship tuple (Auth Helper)
    fastify.post<{
      Body: {
        resource_type: string;
        resource_id: string;
        relation: string;
        subject_type: string;
        subject_id: string;
      };
    }>('/auth/tuples', {
      schema: {
        description: 'Register Zanzibar relation tuple for SpiceDB auth check',
        tags: ['Audience'],
      },
    }, async (request, reply) => {
      const { resource_type, resource_id, relation, subject_type, subject_id } =
        request.body;
      await ctx.auth.writeRelationship(
        resource_type,
        resource_id,
        relation,
        subject_type,
        subject_id
      );
      return reply.code(201).send({ success: true });
    });
  };
}
