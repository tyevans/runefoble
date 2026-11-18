/**
 * DM approval queue for audience modifiers. Governed by ADR-0001 (SpiceDB) and ADR-0006.
 * Proposal state lives in ProposalAggregate event streams. Every decision checks the
 * `audience_poll` permission that matches the command (TASK-0554).
 */

import type { AudienceAccess } from './access/audienceAccess.js';
import { presentProposal } from './access/presentation.js';
import { EventListeners } from './eventListeners.js';
import { proposalStreamId } from './domain/events.js';
import { NotFound } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import type { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import type { AudienceModifierProposal, ProposalStatus, ProposalSummary } from './types.js';

export type ProposalAction = 'queued' | 'approved' | 'vetoed';

export interface ProposalChange {
  action: ProposalAction;
  proposal: AudienceModifierProposal;
}

export class ApprovalQueue {
  private readonly events: EventListeners<ProposalChange>;

  constructor(
    private readonly access: AudienceAccess,
    private readonly repo: AudienceEventRepository,
    private readonly mutex: KeyedMutex,
    log: Logger
  ) {
    this.events = new EventListeners<ProposalChange>(log, 'Proposal listener failed', (change) => ({ action: change.action }));
  }

  onProposalChange(callback: (change: ProposalChange) => void): () => void {
    return this.events.subscribe(callback);
  }

  /** Called by the poll service after a proposal is committed. */
  announceQueued(proposal: AudienceModifierProposal): void {
    this.events.emit({ action: 'queued', proposal });
  }

  /** Proposals of polls the actor can view. Parameters appear only for approvers. One bulk permission call. */
  async getProposals(
    actor: VerifiedPrincipal,
    campaignId?: string,
    status?: ProposalStatus
  ): Promise<Array<AudienceModifierProposal | ProposalSummary>> {
    let list = (await this.repo.loadAllProposals())
      .map((p) => p.snapshot())
      .filter((p): p is AudienceModifierProposal => p !== undefined);
    if (campaignId) {
      list = list.filter((p) => p.campaignId === campaignId);
    }
    if (status) {
      list = list.filter((p) => p.status === status);
    }
    const granted = await this.access.grantedPollPermissions(actor, list.map((p) => p.pollId), ['view', 'approve']);
    const visible: Array<AudienceModifierProposal | ProposalSummary> = [];
    for (const proposal of list) {
      const held = granted.get(proposal.pollId);
      if (!held?.has('view')) continue;
      visible.push(presentProposal(proposal, held.has('approve')));
    }
    return visible;
  }

  approveProposal(proposalId: string, actor: VerifiedPrincipal): Promise<AudienceModifierProposal> {
    return this.decide(proposalId, actor, 'approve', 'approve', 'approved');
  }

  vetoProposal(proposalId: string, actor: VerifiedPrincipal): Promise<AudienceModifierProposal> {
    return this.decide(proposalId, actor, 'reject', 'veto', 'vetoed');
  }

  private async decide(
    proposalId: string,
    actor: VerifiedPrincipal,
    command: 'approve' | 'reject',
    permission: 'approve' | 'veto',
    action: 'approved' | 'vetoed'
  ): Promise<AudienceModifierProposal> {
    const current = await this.repo.loadProposal(proposalId);
    if (!current) {
      throw new NotFound(`Proposal '${proposalId}' not found`);
    }
    await this.access.requirePoll(actor, current.snapshot()!.pollId, permission);

    const decided = await this.mutex.run([proposalStreamId(proposalId)], async () => {
      const proposal = await this.repo.loadProposal(proposalId);
      if (!proposal) {
        throw new NotFound(`Proposal '${proposalId}' not found`);
      }
      proposal[command](actor.userId, new Date());
      await this.repo.commit([proposal]);
      return proposal.snapshot()!;
    });

    this.events.emit({ action, proposal: decided });
    return decided;
  }
}
