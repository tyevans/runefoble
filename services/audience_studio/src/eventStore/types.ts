/**
 * Event store contract for Audience Studio aggregates (ADR-0011 event sourcing).
 * Two implementations exist: PostgreSQL for deployed environments and an
 * in-memory store for tests only.
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
  readonly kind: 'postgresql' | 'memory';
  /** Create storage objects and verify the connection. Throws when the store is unusable. */
  init(): Promise<void>;
  ping(): Promise<boolean>;
  load(streamId: string): Promise<StoredEvent[]>;
  /** All events of every stream whose id starts with the prefix, ordered by stream then version. */
  loadPrefix(prefix: string): Promise<StoredEvent[]>;
  /** Writes every change in one transaction, or none. */
  appendAll(changes: AppendChange[]): Promise<void>;
  close(): Promise<void>;
}
