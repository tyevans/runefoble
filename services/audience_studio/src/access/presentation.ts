/**
 * Caller-specific views of proposals. Proposal parameters reach only principals with
 * `audience_poll.approve` (TASK-0554). Other viewers get the summary fields only.
 */

import type { AudienceModifierProposal, AudiencePoll, AudiencePollRecord, ProposalSummary } from '../types.js';

export function summarizeProposal(proposal: AudienceModifierProposal): ProposalSummary {
  return {
    id: proposal.id,
    pollId: proposal.pollId,
    campaignId: proposal.campaignId,
    sessionId: proposal.sessionId,
    title: proposal.title,
    status: proposal.status,
    createdAt: proposal.createdAt,
    reviewedBy: proposal.reviewedBy,
    reviewedAt: proposal.reviewedAt,
  };
}

export function presentProposal(
  proposal: AudienceModifierProposal,
  canApprove: boolean
): AudienceModifierProposal | ProposalSummary {
  return canApprove ? proposal : summarizeProposal(proposal);
}

/** Takes a poll as the engine builds it, with the full proposal. Returns the caller's view. */
export function presentPoll(poll: AudiencePollRecord, canApprove: boolean): AudiencePoll {
  if (!poll.proposedModifier) return poll;
  return { ...poll, proposedModifier: presentProposal(poll.proposedModifier, canApprove) };
}
