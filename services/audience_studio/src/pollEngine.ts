/**
 * Audience Poll Engine for live high-concurrency spectator voting.
 * Governed by ADR-0006 and ADR-0007.
 */

import { v4 as uuidv4 } from 'uuid';
import type { ApprovalQueue } from './approvalQueue.js';
import {
  buildModifierProposedEvent,
  buildPollCompletedEvent,
  buildPollStartedEvent,
  buildVoteCastEvent,
} from './events.js';
import type { RedisStreamsClient } from './redis.js';
import type {
  AudienceModifierProposal,
  AudiencePoll,
  AudienceVote,
  PollOption,
} from './types.js';

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

export class PollEngine {
  private polls: Map<string, AudiencePoll> = new Map();
  private votersByPoll: Map<string, Set<string>> = new Map();
  private timers: Map<string, NodeJS.Timeout> = new Map();
  private listeners: Array<(event: 'poll_started' | 'vote_cast' | 'poll_completed', data: unknown) => void> = [];

  constructor(
    private readonly redis: RedisStreamsClient,
    private readonly approvalQueue: ApprovalQueue
  ) {}

  onPollEvent(
    callback: (event: 'poll_started' | 'vote_cast' | 'poll_completed', data: unknown) => void
  ): () => void {
    this.listeners.push(callback);
    return () => {
      const idx = this.listeners.indexOf(callback);
      if (idx !== -1) this.listeners.splice(idx, 1);
    };
  }

  private notify(
    event: 'poll_started' | 'vote_cast' | 'poll_completed',
    data: unknown
  ): void {
    for (const listener of this.listeners) {
      try {
        listener(event, data);
      } catch {
        // Ignore listener error
      }
    }
  }

  async createPoll(params: CreatePollParams): Promise<AudiencePoll> {
    const id = uuidv4();
    const duration = params.durationSeconds ?? 60;
    const quorum = params.quorum ?? 5;
    const now = new Date();
    const expires = new Date(now.getTime() + duration * 1000);

    const options: PollOption[] = params.options.map((label, idx) => ({
      id: `opt_${idx + 1}`,
      label,
      votes: 0,
    }));

    const poll: AudiencePoll = {
      id,
      campaignId: params.campaignId,
      sessionId: params.sessionId,
      title: params.title,
      prompt: params.prompt,
      options,
      durationSeconds: duration,
      quorum,
      createdAt: now.toISOString(),
      expiresAt: expires.toISOString(),
      status: 'active',
      totalVotes: 0,
    };

    this.polls.set(id, poll);
    this.votersByPoll.set(id, new Set());

    // Schedule expiration timer
    const timer = setTimeout(() => {
      this.closePoll(id).catch(() => {});
    }, duration * 1000);
    this.timers.set(id, timer);

    // Publish CloudEvent
    const event = buildPollStartedEvent(poll);
    await this.redis.publishEvent('runefoble.events.audience', event);

    this.notify('poll_started', poll);
    return poll;
  }

  async castVote(
    pollId: string,
    voterId: string,
    optionId: string,
    channel: string = 'web'
  ): Promise<AudiencePoll> {
    const poll = this.polls.get(pollId);
    if (!poll) {
      throw new Error(`Poll '${pollId}' not found`);
    }
    if (poll.status !== 'active') {
      throw new Error(`Poll '${pollId}' is no longer active`);
    }

    const option = poll.options.find((o) => o.id === optionId);
    if (!option) {
      throw new Error(`Option '${optionId}' not found in poll '${pollId}'`);
    }

    const voters = this.votersByPoll.get(pollId)!;
    if (voters.has(voterId)) {
      throw new Error(`Voter '${voterId}' has already voted in poll '${pollId}'`);
    }
    voters.add(voterId);

    option.votes += 1;
    poll.totalVotes += 1;

    const vote: AudienceVote = {
      pollId,
      campaignId: poll.campaignId,
      voterId,
      optionId,
      channel,
      timestamp: new Date().toISOString(),
    };

    const event = buildVoteCastEvent(vote);
    await this.redis.publishEvent('runefoble.events.audience', event);

    this.notify('vote_cast', { poll, vote });
    return poll;
  }

  async closePoll(pollId: string): Promise<AudiencePoll> {
    const poll = this.polls.get(pollId);
    if (!poll) {
      throw new Error(`Poll '${pollId}' not found`);
    }
    if (poll.status === 'completed') {
      return poll;
    }

    const timer = this.timers.get(pollId);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(pollId);
    }

    poll.status = 'completed';
    const sorted = [...poll.options].sort((a, b) => b.votes - a.votes);
    const winningOpt = sorted[0];
    poll.winningOptionId = winningOpt?.id;
    poll.quorumMet = poll.totalVotes >= poll.quorum;

    if (poll.quorumMet && winningOpt) {
      const proposal: AudienceModifierProposal = {
        id: uuidv4(),
        pollId: poll.id,
        campaignId: poll.campaignId,
        sessionId: poll.sessionId,
        title: `${poll.title}: ${winningOpt.label}`,
        modifierType: 'chaos_modifier',
        description: `Audience voted for: ${winningOpt.label} (${winningOpt.votes}/${poll.totalVotes} votes)`,
        parameters: {
          winningOptionId: winningOpt.id,
          label: winningOpt.label,
          votes: winningOpt.votes,
          totalVotes: poll.totalVotes,
        },
        status: 'pending',
        createdAt: new Date().toISOString(),
      };
      poll.proposedModifier = proposal;
      this.approvalQueue.enqueueProposal(proposal);

      const propEvent = buildModifierProposedEvent(proposal);
      await this.redis.publishEvent('runefoble.events.audience', propEvent);
    }

    const event = buildPollCompletedEvent(poll);
    await this.redis.publishEvent('runefoble.events.audience', event);

    this.notify('poll_completed', poll);
    return poll;
  }

  getPoll(pollId: string): AudiencePoll | undefined {
    return this.polls.get(pollId);
  }

  listPolls(campaignId?: string): AudiencePoll[] {
    let list = Array.from(this.polls.values());
    if (campaignId) {
      list = list.filter((p) => p.campaignId === campaignId);
    }
    return list;
  }
}
