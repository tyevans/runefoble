/**
 * Event store contract for Audience Studio aggregates (ADR-0011 event sourcing).
 * Production code has one implementation: PostgreSQL. Tests inject an in-memory fake
 * from `test/fakes/`.
 */

export interface NewEvent {
  type: string;
  data: Record<string, unknown>;
  occurredAt: string;
}

export interface StoredEvent extends NewEvent {
  streamId: string;
  version: number;
}

/** Events for one stream. The expected version is the version the writer loaded. */
export interface AppendChange {
  streamId: string;
  expectedVersion: number;
  events: NewEvent[];
}

export class ConcurrencyConflictError extends Error {
  constructor(streamId: string, expectedVersion: number) {
    super(`Stream '${streamId}' changed since version ${expectedVersion}`);
    this.name = 'ConcurrencyConflictError';
  }
}

export interface EventStore {
  /** Create storage objects and verify the connection. Throws when the store is unusable. */
  init(): Promise<void>;
  ping(): Promise<boolean>;
  load(streamId: string): Promise<StoredEvent[]>;
  /** All events of every stream whose id starts with the prefix, ordered by stream then version. */
  loadPrefix(prefix: string): Promise<StoredEvent[]>;
  /**
   * Writes every change and one outbox entry per event in one transaction, or none.
   * @throws ConcurrencyConflictError when a stream is not at the expected version.
   */
  appendAll(changes: AppendChange[]): Promise<void>;
  /**
   * Passes up to `limit` unsent events, oldest first, to `publish`, then marks them sent.
   * The batch is all or nothing: when `publish` rejects, no event in the batch is marked and
   * the error propagates. Delivery is at least once, so consumers dedupe by event id.
   * Resolves with the number of events in the batch.
   */
  drainOutbox(limit: number, publish: (event: StoredEvent) => Promise<void>): Promise<number>;
  close(): Promise<void>;
}
