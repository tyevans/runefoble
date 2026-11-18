/**
 * Sends committed audience events from the outbox to the Redis Stream (ADR-0006).
 *
 * The repository calls `drain` after each commit. A timer retries events that a failed publish
 * left pending, and sends events that another process committed. Event ids derive from stream
 * and version, so a retry sends the same id. Consumers dedupe on that id.
 */

import { buildCloudEvent } from '../domain/events.js';
import type { EventStore, StoredEvent } from '../eventStore/types.js';
import type { Logger } from '../logger.js';
import type { StreamPublisher } from '../streamPublisher.js';

export const AUDIENCE_STREAM = 'runefoble.events.audience';
const BATCH_SIZE = 100;

export class OutboxRelay {
  private timer: NodeJS.Timeout | undefined;
  /** Drains run one at a time inside this process. The tail never rejects. */
  private running: Promise<void> = Promise.resolve();

  constructor(
    private readonly store: EventStore,
    private readonly publisher: StreamPublisher,
    private readonly log: Logger,
    private readonly intervalMs: number
  ) {}

  start(): void {
    this.timer = setInterval(() => void this.drain(), this.intervalMs);
    this.timer.unref();
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
  }

  /**
   * Sends every pending event. A failure is logged, and the events stay pending for the next
   * drain. The caller's command is already committed, so the failure does not reach the caller.
   */
  drain(): Promise<void> {
    this.running = this.running
      .then(() => this.sendPending())
      .catch((err: unknown) => {
        this.log.error(
          { err, stream: AUDIENCE_STREAM },
          'Audience outbox relay failed; events stay pending and are retried'
        );
      });
    return this.running;
  }

  private async sendPending(): Promise<void> {
    let batch: number;
    do {
      batch = await this.store.drainOutbox(BATCH_SIZE, (event) => this.send(event));
    } while (batch === BATCH_SIZE);
  }

  private async send(event: StoredEvent): Promise<void> {
    await this.publisher.publish(AUDIENCE_STREAM, buildCloudEvent(event));
  }
}
