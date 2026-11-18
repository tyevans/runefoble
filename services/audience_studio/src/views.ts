/**
 * JSON views returned by the REST and WebSocket layers. Field names are part of the public contract.
 */

import type { PollSnapshot } from './domain/pollAggregate.js';
import type { AudienceModifierProposal, AudiencePollRecord } from './types.js';

export function pollView(snapshot: PollSnapshot, proposal?: AudienceModifierProposal): AudiencePollRecord {
  return {
    id: snapshot.id,
    campaignId: snapshot.campaignId,
    sessionId: snapshot.sessionId,
    title: snapshot.title,
    prompt: snapshot.prompt,
    options: snapshot.options,
    durationSeconds: snapshot.durationSeconds,
    quorum: snapshot.quorum,
    createdAt: snapshot.createdAt,
    expiresAt: snapshot.expiresAt,
    status: snapshot.status === 'completed' ? 'completed' : 'active',
    winningOptionId: snapshot.winningOptionId,
    quorumMet: snapshot.quorumMet,
    totalVotes: snapshot.totalVotes,
    proposedModifier: proposal,
  };
}
