/**
 * Poll routes: create, list, read, vote, and close. The plugin error handler maps typed errors.
 */

import type { FastifyInstance } from 'fastify';
import { principalOf } from '../identity/principal.js';
import type { PollEngine } from '../pollEngine.js';

interface CreatePollBody {
  campaign_id: string;
  session_id?: string;
  title: string;
  prompt: string;
  options: string[];
  duration_seconds?: number;
  quorum?: number;
  modifier_type?: string;
}

export function registerPollRoutes(fastify: FastifyInstance, pollEngine: PollEngine): void {
  fastify.post<{ Body: CreatePollBody }>('/polls', {
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
    const poll = await pollEngine.createPoll(principalOf(request), {
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

  fastify.get<{ Querystring: { campaign_id?: string } }>('/polls', {
    schema: {
      description: 'List audience polls the caller can view (audience_poll.view).',
      tags: ['Audience'],
    },
  }, async (request) => {
    const polls = await pollEngine.listPolls(principalOf(request), request.query.campaign_id);
    return { polls };
  });

  fastify.get<{ Params: { pollId: string } }>('/polls/:pollId', {
    schema: {
      description: 'Get details and live results of an audience poll (audience_poll.view).',
      tags: ['Audience'],
    },
  }, async (request) => pollEngine.getPoll(request.params.pollId, principalOf(request)));

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
  }, async (request) => {
    const { option_id, channel } = request.body;
    const poll = await pollEngine.castVote(request.params.pollId, principalOf(request), option_id, channel ?? 'web');
    return { success: true, poll };
  });

  fastify.post<{ Params: { pollId: string } }>('/polls/:pollId/close', {
    schema: {
      description: 'Close poll and resolve modifier proposals (audience_poll.moderate).',
      tags: ['Audience'],
    },
  }, async (request) => pollEngine.closePoll(request.params.pollId, principalOf(request)));
}
