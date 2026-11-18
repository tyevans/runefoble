/**
 * Audience poll service for live spectator voting. Governed by ADR-0006 and ADR-0007.
 *
 * State lives in PollAggregate and ProposalAggregate event streams. Timers close the polls
 * (PollCloseScheduler). Views and permission-based presentation live in PollPresenter.
 */

import { v4 as uuidv4 } from 'uuid';
import type { AudienceAccess, PollPermission } from './access/audienceAccess.js';
import { presentPoll } from './access/presentation.js';
import type { ApprovalQueue } from './approvalQueue.js';
import { EventListeners } from './eventListeners.js';
import { PollAggregate, type PollSnapshot } from './domain/pollAggregate.js';
import { ProposalAggregate } from './domain/proposalAggregate.js';
import { pollStreamId } from './domain/events.js';
import { NotFound } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { EventSourcedAggregate } from './eventSourcing/aggregate.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import { PollCloseScheduler } from './pollCloseScheduler.js';
import { PollPresenter } from './pollPresenter.js';
import { pollView } from './views.js';
import type { AudiencePoll, AudiencePollRecord, AudienceVote } from './types.js';

export interface CreatePollParams {
  campaignId: string;
  sessionId?: string;
  title: string;
  prompt: string;
  options: string[];
  durationSeconds?: number;
  quorum?: number;
  modifierType?: string;
}

/** Events published after a poll command commits. Poll records carry full proposals. */
export type PollEvent =
  | { type: 'poll_started'; poll: AudiencePollRecord }
  | { type: 'vote_cast'; poll: AudiencePollRecord; vote: AudienceVote }
  | { type: 'poll_completed'; poll: AudiencePollRecord };

const RESTORED_LOG = 'Restored open audience polls';

export class PollEngine {
  private readonly events: EventListeners<PollEvent>;
  private readonly scheduler: PollCloseScheduler;
  private readonly presenter: PollPresenter;

  constructor(
    private readonly repo: AudienceEventRepository,
    private readonly mutex: KeyedMutex,
    private readonly approvalQueue: ApprovalQueue,
    private readonly access: AudienceAccess,
    private readonly log: Logger
  ) {
    this.events = new EventListeners<PollEvent>(log, 'Audience poll listener failed', (event) => ({ event: event.type }));
    this.scheduler = new PollCloseScheduler((pollId) => this.checkDue(pollId), log);
    this.presenter = new PollPresenter(repo, access);
  }

  onPollEvent(callback: (event: PollEvent) => void): () => void {
    return this.events.subscribe(callback);
  }

  /** Re-arms the close timer of every open poll from its stored deadline. Call once at start-up. */
  async restore(): Promise<void> {
    const polls = await this.repo.loadAllPolls();
    let open = 0;
    for (const poll of polls) {
      const snap = poll.snapshot();
      if (snap.status === 'active') {
        open += 1;
        this.scheduler.arm(snap.id, Date.parse(snap.expiresAt) - Date.now());
      }
    }
    this.log.info({ openPolls: open }, RESTORED_LOG);
  }

  /** Clears every timer. Call on shutdown. */
  close(): void {
    this.scheduler.close();
  }

  /** Opens a poll. The actor needs `run_session` on the campaign. The poll is bound to the campaign before it is stored. */
  async createPoll(actor: VerifiedPrincipal, params: CreatePollParams): Promise<AudiencePoll> {
    await this.access.requireCampaign(actor, params.campaignId, 'run_session');
    const id = uuidv4();
    const durationSeconds = params.durationSeconds ?? 60;
    const poll = new PollAggregate(id);
    poll.start({
      campaignId: params.campaignId,
      sessionId: params.sessionId,
      title: params.title,
      prompt: params.prompt,
      options: params.options,
      durationSeconds,
      quorum: params.quorum ?? 5,
      now: new Date(),
    });
    await this.access.bindPollToCampaign(id, params.campaignId);
    await this.mutex.run([pollStreamId(id)], () => this.repo.commit([poll]));

    const snap = poll.snapshot();
    this.scheduler.arm(id, Date.parse(snap.expiresAt) - Date.now());
    const view = pollView(snap);
    this.events.emit({ type: 'poll_started', poll: view });
    return this.presenter.presentFor(actor, view);
  }

  /** Records one ballot for the actor. The actor needs `vote` on the poll. */
  async castVote(
    pollId: string,
    actor: VerifiedPrincipal,
    optionId: string,
    channel: string = 'web'
  ): Promise<AudiencePoll> {
    await this.authorize(actor, pollId, 'vote');
    const voterId = actor.userId;
    const now = new Date();
    const snap = await this.mutex.run([pollStreamId(pollId)], async () => {
      const poll = await this.requirePoll(pollId);
      poll.vote(voterId, optionId, channel, now);
      await this.repo.commit([poll]);
      return poll.snapshot();
    });

    const view = await this.presenter.viewOf(snap);
    this.events.emit({
      type: 'vote_cast',
      poll: view,
      vote: {
        pollId,
        campaignId: snap.campaignId,
        voterId,
        optionId,
        channel,
        timestamp: now.toISOString(),
      },
    });
    return this.presenter.presentFor(actor, view);
  }

  /** Completes the poll for a moderator. The actor needs `moderate` on the poll. */
  async closePoll(pollId: string, actor: VerifiedPrincipal): Promise<AudiencePoll> {
    await this.authorize(actor, pollId, 'moderate');
    return this.presenter.presentFor(actor, await this.complete(pollId));
  }

  /** Completes the poll. Idempotent: a completed poll is returned unchanged. Used by the timer as well. */
  private async complete(pollId: string): Promise<AudiencePollRecord> {
    const outcome = await this.mutex.run([pollStreamId(pollId)], async () => {
      const poll = await this.requirePoll(pollId);
      if (poll.snapshot().status === 'completed') {
        return { snap: poll.snapshot(), proposal: undefined, closedNow: false };
      }

      const proposalId = uuidv4();
      const proposal = poll.close(proposalId, new Date());
      const changes: EventSourcedAggregate[] = [];
      if (proposal) {
        const queued = new ProposalAggregate(proposalId);
        queued.propose(proposal);
        changes.push(queued);
      }
      changes.push(poll);
      // Proposal first, so the stream sees modifier_proposed before poll_completed.
      await this.repo.commit(changes);
      return { snap: poll.snapshot(), proposal, closedNow: true };
    });

    this.scheduler.disarm(pollId);
    if (outcome.proposal) {
      this.approvalQueue.announceQueued(outcome.proposal);
    }
    const view = await this.presenter.viewOf(outcome.snap);
    if (outcome.closedNow) {
      this.events.emit({ type: 'poll_completed', poll: view });
    }
    return view;
  }

  /** One poll, if the actor can view it. A missing poll is 404 before any permission check. */
  async getPoll(pollId: string, actor: VerifiedPrincipal): Promise<AudiencePoll> {
    await this.authorize(actor, pollId, 'view');
    return this.presenter.presentFor(actor, await this.presenter.viewOf((await this.requirePoll(pollId)).snapshot()));
  }

  /** Polls the actor can view, optionally limited to one campaign. Permissions are checked in one bulk call. */
  async listPolls(actor: VerifiedPrincipal, campaignId?: string): Promise<AudiencePoll[]> {
    const polls = (await this.repo.loadAllPolls()).map((p) => p.snapshot());
    const selected = campaignId ? polls.filter((p) => p.campaignId === campaignId) : polls;
    const proposals = await this.presenter.proposalIndex(selected);
    const granted = await this.access.grantedPollPermissions(actor, selected.map((p) => p.id), ['view', 'approve']);
    const views: AudiencePoll[] = [];
    for (const snap of selected) {
      const held = granted.get(snap.id);
      if (!held?.has('view')) continue;
      const view = pollView(snap, snap.proposalId ? proposals.get(snap.proposalId) : undefined);
      views.push(presentPoll(view, held.has('approve')));
    }
    return views;
  }

  /** Loads the poll (404), then checks the permission (403). */
  private async authorize(actor: VerifiedPrincipal, pollId: string, permission: PollPermission): Promise<void> {
    await this.requirePoll(pollId);
    await this.access.requirePoll(actor, pollId, permission);
  }

  private async requirePoll(pollId: string): Promise<PollAggregate> {
    const poll = await this.repo.loadPoll(pollId);
    if (!poll) {
      throw new NotFound(`Poll '${pollId}' not found`);
    }
    return poll;
  }

  /** Closes the poll when it is due. Returns the wait until the deadline when it is still open. */
  private async checkDue(pollId: string): Promise<number | null> {
    const poll = await this.repo.loadPoll(pollId);
    if (!poll || poll.snapshot().status !== 'active') return null;
    const remaining = Date.parse(poll.snapshot().expiresAt) - Date.now();
    if (remaining > 0) return remaining;
    await this.complete(pollId);
    return null;
  }
}
