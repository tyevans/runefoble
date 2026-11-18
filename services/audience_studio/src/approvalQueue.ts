/**
 * DM approval queue for audience modifiers. Governed by ADR-0001 (SpiceDB) and ADR-0006.
 * Proposal state lives in ProposalAggregate event streams. Every decision checks the
 * `audience_poll` permission that matches the command (TASK-0554).
 */

import type { AudienceAccess } from './access/audienceAccess.js';
import { presentProposal } from './access/presentation.js';
import { proposalStreamId } from './domain/events.js';
import { NotFound } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import type { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import type { AudienceModifierProposal, ProposalStatus, ProposalSummary } from './types.js';

export type ProposalAction = 'queued' | 'approved' | 'vetoed';
type ProposalListener = (action: ProposalAction, proposal: AudienceModifierProposal) => void;

export class ApprovalQueue {
  private readonly listeners: ProposalListener[] = [];

  constructor(
    private readonly access: AudienceAccess,
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

  /** Proposals of polls the actor can view. Parameters appear only for approvers. */
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
    const visible: Array<AudienceModifierProposal | ProposalSummary> = [];
    for (const proposal of list) {
      if (!(await this.access.pollAllows(actor, proposal.pollId, 'view'))) continue;
      const canApprove = await this.access.pollAllows(actor, proposal.pollId, 'approve');
      visible.push(presentProposal(proposal, canApprove));
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
