/**
 * ProposalAggregate: one chaos modifier proposal awaiting DM decision.
 * Approval and veto both raise `modifier_approved`. A veto sets `approved` to false.
 */

import { DomainError } from '../errors.js';
import { EventSourcedAggregate } from '../eventSourcing/aggregate.js';
import type { StoredEvent } from '../eventStore/types.js';
import type { AudienceModifierProposal, ProposalStatus } from '../types.js';
import {
  EVENT,
  proposalStreamId,
  type ModifierDecidedData,
  type ModifierProposedData,
} from './events.js';

interface ProposalState {
  status: 'none' | ProposalStatus;
  proposal?: AudienceModifierProposal;
}

export class ProposalAggregate extends EventSourcedAggregate {
  private state: ProposalState = { status: 'none' };

  constructor(readonly proposalId: string) {
    super(proposalStreamId(proposalId));
  }

  propose(draft: AudienceModifierProposal): void {
    if (this.state.status !== 'none') {
      throw new DomainError(`Proposal '${this.proposalId}' already exists`);
    }
    const data: ModifierProposedData = {
      proposal_id: draft.id,
      poll_id: draft.pollId,
      campaign_id: draft.campaignId,
      session_id: draft.sessionId ?? null,
      title: draft.title,
      modifier_type: draft.modifierType,
      description: draft.description,
      parameters: draft.parameters,
      status: 'pending',
    };
    this.raise({ type: EVENT.modifierProposed, data: data as unknown as Record<string, unknown>, occurredAt: draft.createdAt });
  }

  approve(dmUserId: string, now: Date): void {
    this.decide(true, dmUserId, now);
  }

  reject(dmUserId: string, now: Date): void {
    this.decide(false, dmUserId, now);
  }

  snapshot(): AudienceModifierProposal | undefined {
    const { proposal } = this.state;
    return proposal ? { ...proposal, parameters: { ...proposal.parameters } } : undefined;
  }

  private decide(approved: boolean, dmUserId: string, now: Date): void {
    const { proposal, status } = this.state;
    if (!proposal || status !== 'pending') {
      throw new DomainError(`Proposal '${this.proposalId}' is already ${status === 'none' ? 'missing' : status}`);
    }
    const data: ModifierDecidedData = {
      proposal_id: proposal.id,
      poll_id: proposal.pollId,
      campaign_id: proposal.campaignId,
      session_id: proposal.sessionId ?? null,
      approved_by: dmUserId,
      approved,
      modifier_type: proposal.modifierType,
      parameters: proposal.parameters,
      applied_at: now.toISOString(),
    };
    this.raise({ type: EVENT.modifierApproved, data: data as unknown as Record<string, unknown>, occurredAt: now.toISOString() });
  }

  protected applyEvent(event: StoredEvent): void {
    switch (event.type) {
      case EVENT.modifierProposed: {
        const d = event.data as unknown as ModifierProposedData;
        this.state = {
          status: 'pending',
          proposal: {
            id: d.proposal_id,
            pollId: d.poll_id,
            campaignId: d.campaign_id,
            sessionId: d.session_id ?? undefined,
            title: d.title,
            modifierType: d.modifier_type,
            description: d.description,
            parameters: d.parameters,
            status: 'pending',
            createdAt: event.occurredAt,
          },
        };
        return;
      }
      case EVENT.modifierApproved: {
        const d = event.data as unknown as ModifierDecidedData;
        if (!this.state.proposal) {
          throw new Error(`Decision stored before proposal in ${event.streamId}`);
        }
        const status: ProposalStatus = d.approved ? 'approved' : 'vetoed';
        this.state = {
          status,
          proposal: {
            ...this.state.proposal,
            status,
            reviewedBy: d.approved_by,
            reviewedAt: event.occurredAt,
          },
        };
        return;
      }
      default:
        throw new Error(`Unknown proposal event type '${event.type}' in ${event.streamId}`);
    }
  }
}
