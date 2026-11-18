/**
 * In-memory event store. Used only in tests (NODE_ENV=test without a database URL).
 * Deployed services never select it (ADR-0015 decision f).
 */

import {
  ConcurrencyConflictError,
  type AppendChange,
  type EventStore,
  type StoredEvent,
} from './types.js';

export class MemoryEventStore implements EventStore {
  readonly kind = 'memory' as const;
  private readonly streams = new Map<string, StoredEvent[]>();
  /** Outbox: events committed and not yet sent, in commit order. */
  private unsent: StoredEvent[] = [];

  async init(): Promise<void> {}

  async ping(): Promise<boolean> {
    return true;
  }

  async load(streamId: string): Promise<StoredEvent[]> {
    return [...(this.streams.get(streamId) ?? [])];
  }

  async loadPrefix(prefix: string): Promise<StoredEvent[]> {
    const ids = [...this.streams.keys()].filter((id) => id.startsWith(prefix)).sort();
    return ids.flatMap((id) => this.streams.get(id) ?? []);
  }

  async appendAll(changes: AppendChange[]): Promise<void> {
    // Check every stream first, so a conflict writes nothing.
    for (const change of changes) {
      const current = this.streams.get(change.streamId)?.length ?? 0;
      if (current !== change.expectedVersion) {
        throw new ConcurrencyConflictError(change.streamId, change.expectedVersion);
      }
    }
    for (const change of changes) {
      const appended = change.events.map((event, index): StoredEvent => ({
        ...event,
        streamId: change.streamId,
        version: change.expectedVersion + index + 1,
      }));
      const list = this.streams.get(change.streamId) ?? [];
      list.push(...appended);
      this.streams.set(change.streamId, list);
      this.unsent.push(...appended);
    }
  }

  async drainOutbox(limit: number, publish: (event: StoredEvent) => Promise<void>): Promise<number> {
    const batch = this.unsent.slice(0, limit);
    for (const event of batch) {
      await publish(event);
    }
    this.unsent.splice(0, batch.length);
    return batch.length;
  }

  async close(): Promise<void> {}
}
