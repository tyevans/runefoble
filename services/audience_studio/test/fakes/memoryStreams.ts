/**
 * In-memory stream publisher for tests. Tests inject it through `createAdapters` in `buildServer`.
 * It can simulate an outage and publish failures, so tests can exercise the rejection path.
 * Production code cannot select it (ADR-0015 decision f).
 */

import { DependencyUnavailableError } from '../../src/errors.js';
import type { StreamPublisher } from '../../src/streamPublisher.js';
import type { CloudEvent } from '../../src/types.js';

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
