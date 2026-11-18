/**
 * Audience poll service for live spectator voting. Governed by ADR-0006 and ADR-0007.
 *
 * State lives in PollAggregate and ProposalAggregate event streams. The only in-process
 * state is the timer handles that close each open poll at its deadline.
 */

import { v4 as uuidv4 } from 'uuid';
import type { AudienceAccess, PollPermission } from './access/audienceAccess.js';
import { presentPoll } from './access/presentation.js';
import type { ApprovalQueue } from './approvalQueue.js';
import { PollAggregate, type PollSnapshot } from './domain/pollAggregate.js';
import { ProposalAggregate } from './domain/proposalAggregate.js';
import { pollStreamId } from './domain/events.js';
import { NotFound } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { EventSourcedAggregate } from './eventSourcing/aggregate.js';
import type { Logger } from './logger.js';
import type { VerifiedPrincipal } from './identity/zitadelVerifier.js';
import { pollView } from './views.js';
import type { AudienceModifierProposal, AudiencePoll, AudiencePollRecord, AudienceVote } from './types.js';

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
type PollListener = (event: PollEvent) => void;

const MAX_TIMER_MS = 2 ** 31 - 1;
const RETRY_DELAY_MS = 1000;

export class PollEngine {
  private readonly timers = new Map<string, NodeJS.Timeout>();
  private readonly listeners: PollListener[] = [];

  constructor(
    private readonly repo: AudienceEventRepository,
    private readonly mutex: KeyedMutex,
    private readonly approvalQueue: ApprovalQueue,
    private readonly access: AudienceAccess,
    private readonly log: Logger
  ) {}

  onPollEvent(callback: PollListener): () => void {
    this.listeners.push(callback);
    return () => {
      const idx = this.listeners.indexOf(callback);
      if (idx !== -1) this.listeners.splice(idx, 1);
    };
  }

  /** Re-arms the close timer of every open poll from its stored deadline. Call once at start-up. */
  async restore(): Promise<void> {
    const polls = await this.repo.loadAllPolls();
    let open = 0;
    for (const poll of polls) {
      const snap = poll.snapshot();
      if (snap.status === 'active') {
        open += 1;
        this.schedule(snap.id, Date.parse(snap.expiresAt) - Date.now());
      }
    }
    this.log.info({ openPolls: open }, 'Restored open audience polls');
  }

  /** Clears every timer. Call on shutdown. */
  close(): void {
    for (const handle of this.timers.values()) clearTimeout(handle);
    this.timers.clear();
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
    this.schedule(id, Date.parse(snap.expiresAt) - Date.now());
    const view = pollView(snap);
    this.notify({ type: 'poll_started', poll: view });
    return this.presentFor(actor, view);
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

    const view = await this.viewOf(snap);
    this.notify({
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
    return this.presentFor(actor, view);
  }

  /** Completes the poll for a moderator. The actor needs `moderate` on the poll. */
  async closePoll(pollId: string, actor: VerifiedPrincipal): Promise<AudiencePoll> {
    await this.authorize(actor, pollId, 'moderate');
    return this.presentFor(actor, await this.complete(pollId));
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

    this.clearTimer(pollId);
    if (outcome.proposal) {
      this.approvalQueue.announceQueued(outcome.proposal);
    }
    const view = await this.viewOf(outcome.snap);
    if (outcome.closedNow) {
      this.notify({ type: 'poll_completed', poll: view });
    }
    return view;
  }

  /** One poll, if the actor can view it. A missing poll is 404 before any permission check. */
  async getPoll(pollId: string, actor: VerifiedPrincipal): Promise<AudiencePoll> {
    await this.authorize(actor, pollId, 'view');
    return this.presentFor(actor, await this.viewOf((await this.requirePoll(pollId)).snapshot()));
  }

  /** Polls the actor can view, optionally limited to one campaign. */
  async listPolls(actor: VerifiedPrincipal, campaignId?: string): Promise<AudiencePoll[]> {
    const polls = (await this.repo.loadAllPolls()).map((p) => p.snapshot());
    const selected = campaignId ? polls.filter((p) => p.campaignId === campaignId) : polls;
    const proposals = await this.proposalIndex(selected);
    const views: AudiencePoll[] = [];
    for (const snap of selected) {
      if (!(await this.access.pollAllows(actor, snap.id, 'view'))) continue;
      const view = pollView(snap, snap.proposalId ? proposals.get(snap.proposalId) : undefined);
      views.push(await this.presentFor(actor, view));
    }
    return views;
  }

  /** Loads the poll (404), then checks the permission (403). */
  private async authorize(actor: VerifiedPrincipal, pollId: string, permission: PollPermission): Promise<void> {
    await this.requirePoll(pollId);
    await this.access.requirePoll(actor, pollId, permission);
  }

  /** Strips proposal parameters unless the actor holds `approve` on the poll. */
  private async presentFor(actor: VerifiedPrincipal, view: AudiencePollRecord): Promise<AudiencePoll> {
    if (!view.proposedModifier) return view;
    const canApprove = await this.access.pollAllows(actor, view.id, 'approve');
    return presentPoll(view, canApprove);
  }

  private async requirePoll(pollId: string): Promise<PollAggregate> {
    const poll = await this.repo.loadPoll(pollId);
    if (!poll) {
      throw new NotFound(`Poll '${pollId}' not found`);
    }
    return poll;
  }

  private async viewOf(snap: PollSnapshot): Promise<AudiencePollRecord> {
    let proposal: AudienceModifierProposal | undefined;
    if (snap.proposalId) {
      proposal = (await this.repo.loadProposal(snap.proposalId))?.snapshot();
    }
    return pollView(snap, proposal);
  }

  private async proposalIndex(polls: PollSnapshot[]): Promise<Map<string, AudienceModifierProposal>> {
    if (!polls.some((p) => p.proposalId)) return new Map();
    const index = new Map<string, AudienceModifierProposal>();
    for (const proposal of await this.repo.loadAllProposals()) {
      const snap = proposal.snapshot();
      if (snap) index.set(snap.id, snap);
    }
    return index;
  }

  /** Arms the close timer. The callback re-checks state, so a late or retried fire is harmless. */
  private schedule(pollId: string, delayMs: number): void {
    this.clearTimer(pollId);
    const handle = setTimeout(
      () => {
        this.timers.delete(pollId);
        void this.expire(pollId);
      },
      Math.min(Math.max(delayMs, 0), MAX_TIMER_MS)
    );
    this.timers.set(pollId, handle);
  }

  private clearTimer(pollId: string): void {
    const handle = this.timers.get(pollId);
    if (handle) {
      clearTimeout(handle);
      this.timers.delete(pollId);
    }
  }

  private async expire(pollId: string): Promise<void> {
    try {
      const poll = await this.repo.loadPoll(pollId);
      if (!poll || poll.snapshot().status !== 'active') return;
      const remaining = Date.parse(poll.snapshot().expiresAt) - Date.now();
      if (remaining > 0) {
        this.schedule(pollId, remaining);
        return;
      }
      await this.complete(pollId);
    } catch (err) {
      this.log.error({ err, pollId }, 'Poll expiry failed; retrying');
      this.schedule(pollId, RETRY_DELAY_MS);
    }
  }

  private notify(event: PollEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch (err) {
        // A broken listener must not block the other listeners or the command. The failure is logged.
        this.log.error({ err, event: event.type }, 'Audience poll listener failed');
      }
    }
  }
}

