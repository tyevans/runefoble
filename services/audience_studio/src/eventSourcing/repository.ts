/**
 * Loads and commits Audience Studio aggregates.
 *
 * Commit order: append every event and one outbox entry per event in one transaction. Only a
 * failed append rejects the command. Then the outbox relay sends the events to Redis Streams.
 * A stream event therefore never exists without a stored event.
 */

import { PollAggregate } from '../domain/pollAggregate.js';
import { ProposalAggregate } from '../domain/proposalAggregate.js';
import {
  POLL_STREAM_PREFIX,
  PROPOSAL_STREAM_PREFIX,
  pollStreamId,
  proposalStreamId,
} from '../domain/events.js';
import type { EventStore, StoredEvent } from '../eventStore/types.js';
import type { EventSourcedAggregate } from './aggregate.js';
import type { OutboxRelay } from './outboxRelay.js';

function rehydrated<T extends EventSourcedAggregate>(aggregate: T, events: StoredEvent[]): T {
  aggregate.rehydrate(events);
  return aggregate;
}

export class AudienceEventRepository {
  constructor(
    private readonly store: EventStore,
    private readonly relay: OutboxRelay
  ) {}

  async loadPoll(pollId: string): Promise<PollAggregate | undefined> {
    const events = await this.store.load(pollStreamId(pollId));
    return events.length === 0 ? undefined : rehydrated(new PollAggregate(pollId), events);
  }

  async loadProposal(proposalId: string): Promise<ProposalAggregate | undefined> {
    const events = await this.store.load(proposalStreamId(proposalId));
    return events.length === 0 ? undefined : rehydrated(new ProposalAggregate(proposalId), events);
  }

  async loadAllPolls(): Promise<PollAggregate[]> {
    const grouped = this.group(await this.store.loadPrefix(POLL_STREAM_PREFIX));
    return [...grouped].map(([streamId, events]) =>
      rehydrated(new PollAggregate(streamId.slice(POLL_STREAM_PREFIX.length)), events)
    );
  }

  async loadAllProposals(): Promise<ProposalAggregate[]> {
    const grouped = this.group(await this.store.loadPrefix(PROPOSAL_STREAM_PREFIX));
    return [...grouped].map(([streamId, events]) =>
      rehydrated(new ProposalAggregate(streamId.slice(PROPOSAL_STREAM_PREFIX.length)), events)
    );
  }

  async commit(aggregates: EventSourcedAggregate[]): Promise<void> {
    const changes = aggregates
      .map((aggregate) => aggregate.uncommitted)
      .filter((change): change is NonNullable<typeof change> => change !== undefined);
    if (changes.length === 0) return;

    await this.store.appendAll(changes);
    await this.relay.drain();
  }

  private group(events: StoredEvent[]): Map<string, StoredEvent[]> {
    const grouped = new Map<string, StoredEvent[]>();
    for (const event of events) {
      const list = grouped.get(event.streamId) ?? [];
      list.push(event);
      grouped.set(event.streamId, list);
    }
    return grouped;
  }
}
