/**
 * CloudEvents 1.0 JSON builders for Audience Studio events.
 */

import { v4 as uuidv4 } from 'uuid';
import type {
  AudienceModifierProposal,
  AudiencePoll,
  AudienceVote,
  CloudEvent,
} from './types.js';

export function createCloudEvent<T extends Record<string, unknown>>(
  eventType: string,
  source: string,
  data: T,
  id: string = uuidv4()
): CloudEvent<T> {
  const normType = eventType.startsWith('runefoble.')
    ? eventType
    : `runefoble.events.audience.${eventType}`;
  return {
    specversion: '1.0',
    id,
    source,
    type: normType,
    time: new Date().toISOString(),
    datacontenttype: 'application/json',
    data,
  };
}

export function buildPollStartedEvent(poll: AudiencePoll): CloudEvent {
  return createCloudEvent(
    'runefoble.events.audience.poll_started',
    `/runefoble/audience_poll/${poll.id}`,
    {
      poll_id: poll.id,
      campaign_id: poll.campaignId,
      session_id: poll.sessionId ?? null,
      title: poll.title,
      prompt: poll.prompt,
      options: poll.options,
      duration_seconds: poll.durationSeconds,
      quorum: poll.quorum,
      expires_at: poll.expiresAt,
    }
  );
}

export function buildVoteCastEvent(vote: AudienceVote): CloudEvent {
  return createCloudEvent(
    'runefoble.events.audience.vote_cast',
    `/runefoble/audience_poll/${vote.pollId}`,
    {
      poll_id: vote.pollId,
      campaign_id: vote.campaignId,
      voter_id: vote.voterId,
      option_id: vote.optionId,
      channel: vote.channel,
      timestamp: vote.timestamp,
    }
  );
}

export function buildPollCompletedEvent(poll: AudiencePoll): CloudEvent {
  const winningOpt = poll.options.find((o) => o.id === poll.winningOptionId);
  return createCloudEvent(
    'runefoble.events.audience.poll_completed',
    `/runefoble/audience_poll/${poll.id}`,
    {
      poll_id: poll.id,
      campaign_id: poll.campaignId,
      session_id: poll.sessionId ?? null,
      winning_option_id: poll.winningOptionId ?? null,
      winning_option_label: winningOpt?.label ?? null,
      total_votes: poll.totalVotes,
      quorum_met: poll.quorumMet ?? false,
      proposed_modifier: poll.proposedModifier ?? null,
    }
  );
}

export function buildModifierProposedEvent(
  proposal: AudienceModifierProposal
): CloudEvent {
  return createCloudEvent(
    'runefoble.events.audience.modifier_proposed',
    `/runefoble/audience_proposal/${proposal.id}`,
    {
      proposal_id: proposal.id,
      poll_id: proposal.pollId,
      campaign_id: proposal.campaignId,
      session_id: proposal.sessionId ?? null,
      title: proposal.title,
      modifier_type: proposal.modifierType,
      description: proposal.description,
      parameters: proposal.parameters,
      status: proposal.status,
    }
  );
}

export function buildModifierApprovedEvent(
  proposal: AudienceModifierProposal,
  approvedBy: string,
  approved: boolean = true
): CloudEvent {
  return createCloudEvent(
    'runefoble.events.audience.modifier_approved',
    `/runefoble/audience_proposal/${proposal.id}`,
    {
      proposal_id: proposal.id,
      poll_id: proposal.pollId,
      campaign_id: proposal.campaignId,
      session_id: proposal.sessionId ?? null,
      approved_by: approvedBy,
      approved,
      modifier_type: proposal.modifierType,
      parameters: proposal.parameters,
      applied_at: new Date().toISOString(),
    }
  );
}
