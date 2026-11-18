/**
 * Fan-out registry for in-process domain events. A listener that throws does not block the
 * other listeners or the command that emitted the event. The failure is logged.
 */

import type { Logger } from './logger.js';

export class EventListeners<T> {
  private readonly callbacks: Array<(event: T) => void> = [];

  /**
   * @param failureMessage Log message for a listener that throws.
   * @param describe Fields that identify the event in that log line.
   */
  constructor(
    private readonly log: Logger,
    private readonly failureMessage: string,
    private readonly describe: (event: T) => Record<string, unknown>
  ) {}

  /** Registers a callback. The returned function removes it. */
  subscribe(callback: (event: T) => void): () => void {
    this.callbacks.push(callback);
    return () => {
      const idx = this.callbacks.indexOf(callback);
      if (idx !== -1) this.callbacks.splice(idx, 1);
    };
  }

  emit(event: T): void {
    for (const callback of this.callbacks) {
      try {
        callback(event);
      } catch (err) {
        this.log.error({ err, ...this.describe(event) }, this.failureMessage);
      }
    }
  }
}
