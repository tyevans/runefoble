/**
 * DM approval queue for audience modifiers. Governed by ADR-0001 (SpiceDB) and ADR-0006.
 * Proposal state lives in ProposalAggregate event streams.
 */

import type { ZanzibarClient } from './auth.js';
import { proposalStreamId } from './domain/events.js';
import { DomainError } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import type { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { Logger } from './logger.js';
import type { AudienceModifierProposal, ProposalStatus } from './types.js';

export type ProposalAction = 'queued' | 'approved' | 'vetoed';
type ProposalListener = (action: ProposalAction, proposal: AudienceModifierProposal) => void;

export class ApprovalQueue {
  private readonly listeners: ProposalListener[] = [];

  constructor(
    private readonly auth: ZanzibarClient,
    private readonly repo: AudienceEventRepository,
    private readonly mutex: KeyedMutex,
    private readonly log: Logger
  ) {}

  onProposalChange(callback: ProposalListener): () => void {
    this.listeners.push(callback);
    return () => {
      const idx = this.listeners.indexOf(callback);
      if (idx !== -1) this.listeners.splice(idx, 1);
    };
  }

  /** Called by the poll service after a proposal is committed. */
  announceQueued(proposal: AudienceModifierProposal): void {
    this.notify('queued', proposal);
  }

  async getProposal(proposalId: string): Promise<AudienceModifierProposal | undefined> {
    return (await this.repo.loadProposal(proposalId))?.snapshot();
  }

  async getProposals(campaignId?: string, status?: ProposalStatus): Promise<AudienceModifierProposal[]> {
    let list = (await this.repo.loadAllProposals())
      .map((p) => p.snapshot())
      .filter((p): p is AudienceModifierProposal => p !== undefined);
    if (campaignId) {
      list = list.filter((p) => p.campaignId === campaignId);
    }
    if (status) {
      list = list.filter((p) => p.status === status);
    }
    return list;
  }

  async approveProposal(proposalId: string, dmUserId: string): Promise<AudienceModifierProposal> {
    return this.decide(proposalId, dmUserId, 'approve', 'approved');
  }

  async vetoProposal(proposalId: string, dmUserId: string): Promise<AudienceModifierProposal> {
    return this.decide(proposalId, dmUserId, 'reject', 'vetoed');
  }

  private async decide(
    proposalId: string,
    dmUserId: string,
    command: 'approve' | 'reject',
    action: 'approved' | 'vetoed'
  ): Promise<AudienceModifierProposal> {
    const current = await this.repo.loadProposal(proposalId);
    if (!current) {
      throw new DomainError(`Proposal '${proposalId}' not found`, 404);
    }
    const campaignId = current.snapshot()!.campaignId;
    const isDM = await this.auth.isDungeonMaster(dmUserId, campaignId);
    if (!isDM) {
      throw new DomainError(
        `User '${dmUserId}' does not have dungeon_master permission on campaign '${campaignId}'`,
        403
      );
    }

    const decided = await this.mutex.run([proposalStreamId(proposalId)], async () => {
      const proposal = await this.repo.loadProposal(proposalId);
      if (!proposal) {
        throw new DomainError(`Proposal '${proposalId}' not found`, 404);
      }
      proposal[command](dmUserId, new Date());
      await this.repo.commit([proposal]);
      return proposal.snapshot()!;
    });

    this.notify(action, decided);
    return decided;
  }

  private notify(action: ProposalAction, proposal: AudienceModifierProposal): void {
    for (const listener of this.listeners) {
      try {
        listener(action, proposal);
      } catch (err) {
        // A broken listener must not block the other listeners or the command. The failure is logged.
        this.log.error({ err, action }, 'Proposal listener failed');
      }
    }
  }
}

