/**
 * Core type definitions for services/audience_studio
 */

import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';

export interface PollOption {
  id: string;
  label: string;
  votes: number;
}

export type PollStatus = 'active' | 'completed' | 'expired';

export interface AudiencePoll {
  id: string;
  campaignId: string;
  sessionId?: string;
  title: string;
  prompt: string;
  options: PollOption[];
  durationSeconds: number;
  quorum: number;
  createdAt: string;
  expiresAt: string;
  status: PollStatus;
  winningOptionId?: string;
  quorumMet?: boolean;
  totalVotes: number;
  proposedModifier?: AudienceModifierProposal | ProposalSummary;
}

/** A proposal as a viewer without `audience_poll.approve` sees it. Parameters are omitted. */
export type ProposalSummary = Omit<AudienceModifierProposal, 'modifierType' | 'description' | 'parameters'>;

/** A poll with the full proposal, as the engine stores it. Only the access layer turns it into a caller view. */
export type AudiencePollRecord = Omit<AudiencePoll, 'proposedModifier'> & {
  proposedModifier?: AudienceModifierProposal;
};

export interface AudienceVote {
  pollId: string;
  campaignId: string;
  voterId: string;
  optionId: string;
  channel: string;
  timestamp: string;
}

export type ProposalStatus = 'pending' | 'approved' | 'vetoed';

export interface AudienceModifierProposal {
  id: string;
  pollId: string;
  campaignId: string;
  sessionId?: string;
  title: string;
  modifierType: string;
  description: string;
  parameters: Record<string, unknown>;
  status: ProposalStatus;
  createdAt: string;
  reviewedBy?: string;
  reviewedAt?: string;
}

export interface CloudEvent<T = Record<string, unknown>> {
  specversion: '1.0';
  id: string;
  source: string;
  type: string;
  time: string;
  datacontenttype: 'application/json';
  data: T;
}

export interface WSClientMessage {
  action: 'subscribe' | 'cast_vote' | 'approve_proposal' | 'veto_proposal' | 'ping';
  campaignId?: string;
  pollId?: string;
  optionId?: string;
  proposalId?: string;
  channel?: string;
}

/** Fixed codes for `error` frames. The message text is client-safe; internal detail is logged on the server. */
export type WSErrorCode = 'invalid_message' | 'unknown_action' | 'forbidden' | 'rejected' | 'internal_error';

export interface WSServerMessage {
  type:
    | 'connected'
    | 'subscribed'
    | 'poll_started'
    | 'vote_cast'
    | 'poll_completed'
    | 'proposal_queued'
    | 'proposal_approved'
    | 'proposal_vetoed'
    | 'error'
    | 'pong';
  data?: unknown;
  message?: string;
  code?: WSErrorCode;
}

/** A verified socket principal, fixed at the handshake. Every action acts as this principal. */
export interface ClientContext {
  campaignId: string;
  principal: VerifiedPrincipal;
}
