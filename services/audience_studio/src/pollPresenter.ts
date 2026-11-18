/**
 * Builds the poll views that leave the service. A view carries the proposal of a closed poll.
 * Proposal parameters reach only callers with `audience_poll.approve` (TASK-0554).
 */

import type { AudienceAccess } from './access/audienceAccess.js';
import { presentPoll } from './access/presentation.js';
import type { PollSnapshot } from './domain/pollAggregate.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import { pollView } from './views.js';
import type { AudienceModifierProposal, AudiencePoll, AudiencePollRecord } from './types.js';

export class PollPresenter {
  constructor(
    private readonly repo: AudienceEventRepository,
    private readonly access: AudienceAccess
  ) {}

  /** The stored poll with its proposal attached, when one exists. */
  async viewOf(snap: PollSnapshot): Promise<AudiencePollRecord> {
    let proposal: AudienceModifierProposal | undefined;
    if (snap.proposalId) {
      proposal = (await this.repo.loadProposal(snap.proposalId))?.snapshot();
    }
    return pollView(snap, proposal);
  }

  /** Proposals of the given polls, keyed by proposal id. The proposal log is read only when a poll has a proposal. */
  async proposalIndex(polls: PollSnapshot[]): Promise<Map<string, AudienceModifierProposal>> {
    if (!polls.some((p) => p.proposalId)) return new Map();
    const index = new Map<string, AudienceModifierProposal>();
    for (const proposal of await this.repo.loadAllProposals()) {
      const snap = proposal.snapshot();
      if (snap) index.set(snap.id, snap);
    }
    return index;
  }

  /** One poll, as this actor may see it. Costs one permission check, and only when a proposal exists. */
  async presentFor(actor: VerifiedPrincipal, view: AudiencePollRecord): Promise<AudiencePoll> {
    if (!view.proposedModifier) return view;
    const canApprove = await this.access.pollAllows(actor, view.id, 'approve');
    return presentPoll(view, canApprove);
  }
}
