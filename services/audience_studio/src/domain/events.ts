/**
 * Audience event types, stream ids, and CloudEvents 1.0 wire builder.
 * Field names match libs/runefoble_events/src/runefoble_events/audience.py.
 */

import type { AudienceModifierProposal, CloudEvent, PollOption } from '../types.js';

export const EVENT_PREFIX = 'runefoble.events.audience.';

export const EVENT = {
  pollStarted: `${EVENT_PREFIX}poll_started`,
  voteCast: `${EVENT_PREFIX}vote_cast`,
  pollCompleted: `${EVENT_PREFIX}poll_completed`,
  modifierProposed: `${EVENT_PREFIX}modifier_proposed`,
  modifierApproved: `${EVENT_PREFIX}modifier_approved`,
} as const;

export const POLL_STREAM_PREFIX = 'AudiencePoll-';
export const PROPOSAL_STREAM_PREFIX = 'AudienceModifierProposal-';

export const pollStreamId = (pollId: string): string => `${POLL_STREAM_PREFIX}${pollId}`;
export const proposalStreamId = (proposalId: string): string => `${PROPOSAL_STREAM_PREFIX}${proposalId}`;

export interface PollStartedData {
  poll_id: string;
  campaign_id: string;
  session_id: string | null;
  title: string;
  prompt: string;
  options: PollOption[];
  duration_seconds: number;
  quorum: number;
  expires_at: string;
}

export interface VoteCastData {
  poll_id: string;
  campaign_id: string;
  voter_id: string;
  option_id: string;
  channel: string;
  timestamp: string;
}

export interface PollCompletedData {
  poll_id: string;
  campaign_id: string;
  session_id: string | null;
  winning_option_id: string | null;
  winning_option_label: string | null;
  total_votes: number;
  quorum_met: boolean;
  proposed_modifier: AudienceModifierProposal | null;
}

export interface ModifierProposedData {
  proposal_id: string;
  poll_id: string;
  campaign_id: string;
  session_id: string | null;
  title: string;
  modifier_type: string;
  description: string;
  parameters: Record<string, unknown>;
  status: string;
}

/** Emitted for both decisions. `approved` is false for a veto. */
export interface ModifierDecidedData {
  proposal_id: string;
  poll_id: string;
  campaign_id: string;
  session_id: string | null;
  approved_by: string;
  approved: boolean;
  modifier_type: string;
  parameters: Record<string, unknown>;
  applied_at: string;
}

/** Builds the CloudEvent for a stored event. The id is stable for a given stream version. */
export function buildCloudEvent(input: {
  streamId: string;
  version: number;
  type: string;
  data: Record<string, unknown>;
  occurredAt: string;
}): CloudEvent {
  const isProposal = input.streamId.startsWith(PROPOSAL_STREAM_PREFIX);
  const entityId = input.streamId.slice(
    isProposal ? PROPOSAL_STREAM_PREFIX.length : POLL_STREAM_PREFIX.length
  );
  return {
    specversion: '1.0',
    id: `${input.streamId}#${input.version}`,
    source: `/runefoble/${isProposal ? 'audience_proposal' : 'audience_poll'}/${entityId}`,
    type: input.type,
    time: input.occurredAt,
    datacontenttype: 'application/json',
    data: input.data,
  };
}
