/**
 * Timers that close each open poll at its deadline. The only in-process state of the poll
 * service. The timer callback asks the owner whether the poll is still due. A failed check is
 * retried, so a late or repeated fire is harmless.
 */

import type { Logger } from './logger.js';

/** Node's timer delay limit. Longer waits are split by re-arming. */
const MAX_TIMER_MS = 2 ** 31 - 1;
const RETRY_DELAY_MS = 1000;

/**
 * Returns the milliseconds until the poll is due again, or null when nothing is left to do.
 * Throws when the check fails. The scheduler then retries.
 */
export type DueCheck = (pollId: string) => Promise<number | null>;

export class PollCloseScheduler {
  private readonly timers = new Map<string, NodeJS.Timeout>();

  constructor(
    private readonly checkDue: DueCheck,
    private readonly log: Logger
  ) {}

  /** Arms the close timer. An earlier timer for the same poll is replaced. */
  arm(pollId: string, delayMs: number): void {
    this.disarm(pollId);
    const handle = setTimeout(
      () => {
        this.timers.delete(pollId);
        void this.fire(pollId);
      },
      Math.min(Math.max(delayMs, 0), MAX_TIMER_MS)
    );
    this.timers.set(pollId, handle);
  }

  disarm(pollId: string): void {
    const handle = this.timers.get(pollId);
    if (handle) {
      clearTimeout(handle);
      this.timers.delete(pollId);
    }
  }

  /** Clears every timer. Call on shutdown. */
  close(): void {
    for (const handle of this.timers.values()) clearTimeout(handle);
    this.timers.clear();
  }

  private async fire(pollId: string): Promise<void> {
    try {
      const remaining = await this.checkDue(pollId);
      if (remaining !== null) this.arm(pollId, remaining);
    } catch (err) {
      this.log.error({ err, pollId }, 'Poll expiry failed; retrying');
      this.arm(pollId, RETRY_DELAY_MS);
    }
  }
}
