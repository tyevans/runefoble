/**
 * Base class for event-sourced aggregates (Hard Invariant 2, TypeScript flavour).
 * Commands call `raise`. The repository persists `uncommitted` after publishing.
 */

import type { AppendChange, NewEvent, StoredEvent } from '../eventStore/types.js';

export abstract class EventSourcedAggregate {
  private loadedVersion = 0;
  private currentVersion = 0;
  private readonly pending: NewEvent[] = [];

  protected constructor(readonly streamId: string) {}

  /** Replays stored events. Call once, on a fresh instance, before any command. */
  rehydrate(events: readonly StoredEvent[]): void {
    for (const event of events) {
      this.applyEvent(event);
      this.currentVersion = event.version;
    }
    this.loadedVersion = this.currentVersion;
  }

  /** The changes this command produced, or undefined when it produced none. */
  get uncommitted(): AppendChange | undefined {
    if (this.pending.length === 0) return undefined;
    return {
      streamId: this.streamId,
      expectedVersion: this.loadedVersion,
      events: [...this.pending],
    };
  }

  protected raise(event: NewEvent): void {
    this.applyEvent({
      ...event,
      streamId: this.streamId,
      version: this.currentVersion + 1,
    });
    this.currentVersion += 1;
    this.pending.push(event);
  }

  protected abstract applyEvent(event: StoredEvent): void;
}
