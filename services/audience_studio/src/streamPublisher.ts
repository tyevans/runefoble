/**
 * Publishes CloudEvents to a Redis Stream. Implementations: Redis (deployed) and in-memory (tests).
 */

import type { CloudEvent } from './types.js';

export interface StreamPublisher {
  /** Appends the event and resolves with the stream entry id. Rejects when the event is not stored. */
  publish(stream: string, event: CloudEvent): Promise<string>;
  /** True when a publish would reach the stream now. Never throws. */
  ping(): Promise<boolean>;
  close(): Promise<void>;
}
