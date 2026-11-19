/**
 * Modifier proposal routes: list, approve, and veto. The DM decides through SpiceDB permissions.
 * The plugin error handler maps typed errors.
 */

import type { FastifyInstance } from 'fastify';
import type { ApprovalQueue } from '../approvalQueue.js';
import { principalOf } from '../identity/principal.js';
import type { ProposalStatus } from '../types.js';

export function registerProposalRoutes(fastify: FastifyInstance, approvalQueue: ApprovalQueue): void {
  fastify.get<{
    Querystring: { campaign_id?: string; status?: ProposalStatus };
  }>('/proposals', {
    schema: {
      description: 'List modifier proposals the caller can view. Parameters appear only with audience_poll.approve.',
      tags: ['Audience'],
    },
  }, async (request) => {
    const proposals = await approvalQueue.getProposals(
      principalOf(request),
      request.query.campaign_id,
      request.query.status
    );
    return { proposals };
  });

  fastify.post<{ Params: { proposalId: string } }>('/proposals/:proposalId/approve', {
    schema: {
      description: 'Approve chaos modifier proposal (audience_poll.approve). The actor is the token subject.',
      tags: ['Audience'],
    },
  }, async (request) => {
    const proposal = await approvalQueue.approveProposal(request.params.proposalId, principalOf(request));
    return { success: true, proposal };
  });

  fastify.post<{ Params: { proposalId: string } }>('/proposals/:proposalId/veto', {
    schema: {
      description: 'Veto chaos modifier proposal (audience_poll.veto). The actor is the token subject.',
      tags: ['Audience'],
    },
  }, async (request) => {
    const proposal = await approvalQueue.vetoProposal(request.params.proposalId, principalOf(request));
    return { success: true, proposal };
  });
}
