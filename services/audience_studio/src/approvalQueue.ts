/**
 * DM Approval Queue for audience modifiers.
 * Governed by ADR-0001 (SpiceDB Zanzibar) and ADR-0006 (Redis Streams).
 */

import type { ZanzibarClient } from './auth.js';
import { buildModifierApprovedEvent } from './events.js';
import type { RedisStreamsClient } from './redis.js';
import type { AudienceModifierProposal, ProposalStatus } from './types.js';

export class ApprovalQueue {
  private proposals: Map<string, AudienceModifierProposal> = new Map();
  private listeners: Array<
    (action: 'queued' | 'approved' | 'vetoed', proposal: AudienceModifierProposal) => void
  > = [];

  constructor(
    private readonly auth: ZanzibarClient,
    private readonly redis: RedisStreamsClient
  ) {}

  onProposalChange(
    callback: (
      action: 'queued' | 'approved' | 'vetoed',
      proposal: AudienceModifierProposal
    ) => void
  ): () => void {
    this.listeners.push(callback);
    return () => {
      const idx = this.listeners.indexOf(callback);
      if (idx !== -1) this.listeners.splice(idx, 1);
    };
  }

  private notify(
    action: 'queued' | 'approved' | 'vetoed',
    proposal: AudienceModifierProposal
  ): void {
    for (const listener of this.listeners) {
      try {
        listener(action, proposal);
      } catch {
        // Ignore listener error
      }
    }
  }

  enqueueProposal(proposal: AudienceModifierProposal): void {
    this.proposals.set(proposal.id, proposal);
    this.notify('queued', proposal);
  }

  getProposal(proposalId: string): AudienceModifierProposal | undefined {
    return this.proposals.get(proposalId);
  }

  getProposals(
    campaignId?: string,
    status?: ProposalStatus
  ): AudienceModifierProposal[] {
    let list = Array.from(this.proposals.values());
    if (campaignId) {
      list = list.filter((p) => p.campaignId === campaignId);
    }
    if (status) {
      list = list.filter((p) => p.status === status);
    }
    return list;
  }

  async approveProposal(
    proposalId: string,
    dmUserId: string
  ): Promise<AudienceModifierProposal> {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) {
      throw new Error(`Proposal '${proposalId}' not found`);
    }

    const isDM = await this.auth.isDungeonMaster(dmUserId, proposal.campaignId);
    if (!isDM) {
      throw new Error(
        `User '${dmUserId}' does not have dungeon_master permission on campaign '${proposal.campaignId}'`
      );
    }

    proposal.status = 'approved';
    proposal.reviewedBy = dmUserId;
    proposal.reviewedAt = new Date().toISOString();

    // Publish CloudEvent to Redis Streams
    const event = buildModifierApprovedEvent(proposal, dmUserId, true);
    await this.redis.publishEvent('runefoble.events.audience', event);

    this.notify('approved', proposal);
    return proposal;
  }

  async vetoProposal(
    proposalId: string,
    dmUserId: string
  ): Promise<AudienceModifierProposal> {
    const proposal = this.proposals.get(proposalId);
    if (!proposal) {
      throw new Error(`Proposal '${proposalId}' not found`);
    }

    const isDM = await this.auth.isDungeonMaster(dmUserId, proposal.campaignId);
    if (!isDM) {
      throw new Error(
        `User '${dmUserId}' does not have dungeon_master permission on campaign '${proposal.campaignId}'`
      );
    }

    proposal.status = 'vetoed';
    proposal.reviewedBy = dmUserId;
    proposal.reviewedAt = new Date().toISOString();

    this.notify('vetoed', proposal);
    return proposal;
  }
}
