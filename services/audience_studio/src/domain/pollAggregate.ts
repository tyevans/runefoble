/**
 * PollAggregate: the state of one live audience poll (ADR-0007, Hard Invariant 2).
 * Commands validate and raise events. Events rebuild state.
 */

import { DomainError } from '../errors.js';
import { EventSourcedAggregate } from '../eventSourcing/aggregate.js';
import type { StoredEvent } from '../eventStore/types.js';
import type { AudienceModifierProposal, PollOption } from '../types.js';
import {
  EVENT,
  pollStreamId,
  type PollCompletedData,
  type PollStartedData,
  type VoteCastData,
} from './events.js';

export interface StartPollInput {
  campaignId: string;
  sessionId?: string;
  title: string;
  prompt: string;
  options: string[];
  durationSeconds: number;
  quorum: number;
  now: Date;
}

export interface PollSnapshot {
  id: string;
  campaignId: string;
  sessionId?: string;
  title: string;
  prompt: string;
  options: PollOption[];
  durationSeconds: number;
  quorum: number;
  createdAt: string;
  expiresAt: string;
  status: 'none' | 'active' | 'completed';
  totalVotes: number;
  winningOptionId?: string;
  quorumMet?: boolean;
  proposalId?: string;
}

const EMPTY: PollSnapshot = {
  id: '',
  campaignId: '',
  title: '',
  prompt: '',
  options: [],
  durationSeconds: 0,
  quorum: 0,
  createdAt: '',
  expiresAt: '',
  status: 'none',
  totalVotes: 0,
};

export class PollAggregate extends EventSourcedAggregate {
  private state: PollSnapshot = { ...EMPTY, options: [] };
  private readonly voters = new Set<string>();

  constructor(readonly pollId: string) {
    super(pollStreamId(pollId));
  }

  start(input: StartPollInput): void {
    if (this.state.status !== 'none') {
      throw new DomainError(`Poll '${this.pollId}' already exists`);
    }
    const expiresAt = new Date(input.now.getTime() + input.durationSeconds * 1000);
    const data: PollStartedData = {
      poll_id: this.pollId,
      campaign_id: input.campaignId,
      session_id: input.sessionId ?? null,
      title: input.title,
      prompt: input.prompt,
      options: input.options.map((label, index) => ({
        id: `opt_${index + 1}`,
        label,
        votes: 0,
      })),
      duration_seconds: input.durationSeconds,
      quorum: input.quorum,
      expires_at: expiresAt.toISOString(),
    };
    this.raise({ type: EVENT.pollStarted, data: data as unknown as Record<string, unknown>, occurredAt: input.now.toISOString() });
  }

  vote(voterId: string, optionId: string, channel: string, now: Date): void {
    const { state } = this;
    if (state.status !== 'active' || now.getTime() >= Date.parse(state.expiresAt)) {
      throw new DomainError(`Poll '${this.pollId}' is no longer active`);
    }
    if (!state.options.some((o) => o.id === optionId)) {
      throw new DomainError(`Option '${optionId}' not found in poll '${this.pollId}'`);
    }
    if (this.voters.has(voterId)) {
      throw new DomainError(`Voter '${voterId}' has already voted in poll '${this.pollId}'`);
    }
    const data: VoteCastData = {
      poll_id: this.pollId,
      campaign_id: state.campaignId,
      voter_id: voterId,
      option_id: optionId,
      channel,
      timestamp: now.toISOString(),
    };
    this.raise({ type: EVENT.voteCast, data: data as unknown as Record<string, unknown>, occurredAt: now.toISOString() });
  }

  /**
   * Completes the poll. Returns the modifier proposal when quorum is met, or undefined.
   * The caller passes the proposal id and commits the proposal in the same batch.
   */
  close(proposalId: string, now: Date): AudienceModifierProposal | undefined {
    const { state } = this;
    if (state.status !== 'active') {
      throw new DomainError(`Poll '${this.pollId}' is not active`);
    }
    const ranked = [...state.options].sort((a, b) => b.votes - a.votes);
    const winner = ranked[0];
    const quorumMet = state.totalVotes >= state.quorum;
    const proposal: AudienceModifierProposal | undefined =
      quorumMet && winner
        ? {
            id: proposalId,
            pollId: this.pollId,
            campaignId: state.campaignId,
            sessionId: state.sessionId,
            title: `${state.title}: ${winner.label}`,
            modifierType: 'chaos_modifier',
            description: `Audience voted for: ${winner.label} (${winner.votes}/${state.totalVotes} votes)`,
            parameters: {
              winningOptionId: winner.id,
              label: winner.label,
              votes: winner.votes,
              totalVotes: state.totalVotes,
            },
            status: 'pending',
            createdAt: now.toISOString(),
          }
        : undefined;

    const data: PollCompletedData = {
      poll_id: this.pollId,
      campaign_id: state.campaignId,
      session_id: state.sessionId ?? null,
      winning_option_id: winner?.id ?? null,
      winning_option_label: winner?.label ?? null,
      total_votes: state.totalVotes,
      quorum_met: quorumMet,
      proposed_modifier: proposal ?? null,
    };
    this.raise({ type: EVENT.pollCompleted, data: data as unknown as Record<string, unknown>, occurredAt: now.toISOString() });
    return proposal;
  }

  snapshot(): PollSnapshot {
    return { ...this.state, options: this.state.options.map((o) => ({ ...o })) };
  }

  protected applyEvent(event: StoredEvent): void {
    switch (event.type) {
      case EVENT.pollStarted: {
        const d = event.data as unknown as PollStartedData;
        this.voters.clear();
        this.state = {
          id: d.poll_id,
          campaignId: d.campaign_id,
          sessionId: d.session_id ?? undefined,
          title: d.title,
          prompt: d.prompt,
          options: d.options.map((o) => ({ id: o.id, label: o.label, votes: 0 })),
          durationSeconds: d.duration_seconds,
          quorum: d.quorum,
          createdAt: event.occurredAt,
          expiresAt: d.expires_at,
          status: 'active',
          totalVotes: 0,
        };
        return;
      }
      case EVENT.voteCast: {
        const d = event.data as unknown as VoteCastData;
        this.voters.add(d.voter_id);
        const option = this.state.options.find((o) => o.id === d.option_id);
        if (!option) throw new Error(`Stored vote references unknown option '${d.option_id}'`);
        option.votes += 1;
        this.state.totalVotes += 1;
        return;
      }
      case EVENT.pollCompleted: {
        const d = event.data as unknown as PollCompletedData;
        this.state = {
          ...this.state,
          status: 'completed',
          winningOptionId: d.winning_option_id ?? undefined,
          quorumMet: d.quorum_met,
          proposalId: d.proposed_modifier?.id,
        };
        return;
      }
      default:
        throw new Error(`Unknown poll event type '${event.type}' in ${event.streamId}`);
    }
  }
}
