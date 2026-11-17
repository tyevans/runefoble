/**
 * In-memory stream publisher. Used only in tests (REDIS_URL=mock://...). It can simulate an
 * outage and publish failures, so tests can exercise the rejection path.
 */

import { DependencyUnavailableError } from './errors.js';
import type { StreamPublisher } from './streamPublisher.js';
import type { CloudEvent } from './types.js';

export class InMemoryStreamPublisher implements StreamPublisher {
  readonly published: CloudEvent[] = [];
  private reachable = true;
  private failures = 0;

  setReachable(reachable: boolean): void {
    this.reachable = reachable;
  }

  failNextPublishes(count: number): void {
    this.failures = count;
  }

  async publish(stream: string, event: CloudEvent): Promise<string> {
    if (!this.reachable) {
      throw new DependencyUnavailableError(`Stream '${stream}' is unreachable`);
    }
    if (this.failures > 0) {
      this.failures -= 1;
      throw new DependencyUnavailableError(`Injected publish failure on '${stream}'`);
    }
    this.published.push(event);
    return `${this.published.length}-0`;
  }

  async ping(): Promise<boolean> {
    return this.reachable;
  }

  async close(): Promise<void> {}
}
