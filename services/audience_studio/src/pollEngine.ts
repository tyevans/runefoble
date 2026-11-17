/**
 * Audience poll service for live spectator voting. Governed by ADR-0006 and ADR-0007.
 *
 * State lives in PollAggregate and ProposalAggregate event streams. The only in-process
 * state is the timer handles that close each open poll at its deadline.
 */

import { v4 as uuidv4 } from 'uuid';
import type { ApprovalQueue } from './approvalQueue.js';
import { PollAggregate, type PollSnapshot } from './domain/pollAggregate.js';
import { ProposalAggregate } from './domain/proposalAggregate.js';
import { pollStreamId } from './domain/events.js';
import { DomainError } from './errors.js';
import type { AudienceEventRepository } from './eventSourcing/repository.js';
import { KeyedMutex } from './eventSourcing/keyedMutex.js';
import type { EventSourcedAggregate } from './eventSourcing/aggregate.js';
import type { Logger } from './logger.js';
import { pollView } from './views.js';
import type { AudienceModifierProposal, AudiencePoll } from './types.js';

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

export type PollEventName = 'poll_started' | 'vote_cast' | 'poll_completed';
type PollListener = (event: PollEventName, data: unknown) => void;

const MAX_TIMER_MS = 2 ** 31 - 1;
const RETRY_DELAY_MS = 1000;

export class PollEngine {
  private readonly timers = new Map<string, NodeJS.Timeout>();
  private readonly listeners: PollListener[] = [];

  constructor(
    private readonly repo: AudienceEventRepository,
    private readonly mutex: KeyedMutex,
    private readonly approvalQueue: ApprovalQueue,
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

  async createPoll(params: CreatePollParams): Promise<AudiencePoll> {
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
    await this.mutex.run([pollStreamId(id)], () => this.repo.commit([poll]));

    const snap = poll.snapshot();
    this.schedule(id, Date.parse(snap.expiresAt) - Date.now());
    const view = pollView(snap);
    this.notify('poll_started', view);
    return view;
  }

  async castVote(
    pollId: string,
    voterId: string,
    optionId: string,
    channel: string = 'web'
  ): Promise<AudiencePoll> {
    const now = new Date();
    const snap = await this.mutex.run([pollStreamId(pollId)], async () => {
      const poll = await this.requirePoll(pollId);
      poll.vote(voterId, optionId, channel, now);
      await this.repo.commit([poll]);
      return poll.snapshot();
    });

    const view = await this.viewOf(snap);
    this.notify('vote_cast', {
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
    return view;
  }

  /** Completes the poll. Idempotent: a completed poll is returned unchanged. */
  async closePoll(pollId: string): Promise<AudiencePoll> {
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
      this.notify('poll_completed', view);
    }
    return view;
  }

  async getPoll(pollId: string): Promise<AudiencePoll | undefined> {
    const poll = await this.repo.loadPoll(pollId);
    return poll ? this.viewOf(poll.snapshot()) : undefined;
  }

  async listPolls(campaignId?: string): Promise<AudiencePoll[]> {
    const polls = (await this.repo.loadAllPolls()).map((p) => p.snapshot());
    const selected = campaignId ? polls.filter((p) => p.campaignId === campaignId) : polls;
    const proposals = await this.proposalIndex(selected);
    return selected.map((snap) => pollView(snap, snap.proposalId ? proposals.get(snap.proposalId) : undefined));
  }

  private async requirePoll(pollId: string): Promise<PollAggregate> {
    const poll = await this.repo.loadPoll(pollId);
    if (!poll) {
      throw new DomainError(`Poll '${pollId}' not found`, 404);
    }
    return poll;
  }

  private async viewOf(snap: PollSnapshot): Promise<AudiencePoll> {
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
      await this.closePoll(pollId);
    } catch (err) {
      this.log.error({ err, pollId }, 'Poll expiry failed; retrying');
      this.schedule(pollId, RETRY_DELAY_MS);
    }
  }

  private notify(event: PollEventName, data: unknown): void {
    for (const listener of this.listeners) {
      try {
        listener(event, data);
      } catch (err) {
        // A broken listener must not block the other listeners or the command. The failure is logged.
        this.log.error({ err, event }, 'Audience poll listener failed');
      }
    }
  }
}

