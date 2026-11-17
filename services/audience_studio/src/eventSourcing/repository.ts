/**
 * Loads and commits Audience Studio aggregates.
 *
 * Commit order: check the stream bus, publish each event to Redis Streams, then persist.
 * A publish failure throws before anything is persisted, so the command is rejected with no
 * state change. A failure after an earlier publish can leave those events published. That
 * case is logged with the stream and event type.
 */

import { PollAggregate } from '../domain/pollAggregate.js';
import { ProposalAggregate } from '../domain/proposalAggregate.js';
import {
  buildCloudEvent,
  POLL_STREAM_PREFIX,
  PROPOSAL_STREAM_PREFIX,
  pollStreamId,
  proposalStreamId,
} from '../domain/events.js';
import { DependencyUnavailableError } from '../errors.js';
import type { Logger } from '../logger.js';
import type { EventStore, StoredEvent } from '../eventStore/types.js';
import type { StreamPublisher } from '../streamPublisher.js';
import type { CloudEvent } from '../types.js';
import type { EventSourcedAggregate } from './aggregate.js';

export const AUDIENCE_STREAM = 'runefoble.events.audience';

function rehydrated<T extends EventSourcedAggregate>(aggregate: T, events: StoredEvent[]): T {
  aggregate.rehydrate(events);
  return aggregate;
}

export class AudienceEventRepository {
  constructor(
    private readonly store: EventStore,
    private readonly publisher: StreamPublisher,
    private readonly log: Logger
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

    if (!(await this.publisher.ping())) {
      throw new DependencyUnavailableError('Redis Streams is unavailable; the command was not applied');
    }

    for (const change of changes) {
      for (const [index, event] of change.events.entries()) {
        // Event ids derive from stream and version, so a retried command publishes the same id.
        const cloud: CloudEvent = buildCloudEvent({
          streamId: change.streamId,
          version: change.expectedVersion + index + 1,
          type: event.type,
          data: event.data,
          occurredAt: event.occurredAt,
        });
        try {
          await this.publisher.publish(AUDIENCE_STREAM, cloud);
        } catch (err) {
          this.log.error(
            { err, stream: AUDIENCE_STREAM, eventType: event.type, streamId: change.streamId },
            'Failed to publish audience event; command rejected'
          );
          throw err;
        }
      }
    }

    await this.store.appendAll(changes);
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
