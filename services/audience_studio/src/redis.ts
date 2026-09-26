/**
 * Redis Streams publisher and consumer with in-memory fallback.
 */

import { Redis } from 'ioredis';
import type { CloudEvent } from './types.js';

export interface PublishedEntry {
  stream: string;
  id: string;
  event: CloudEvent;
}

export class RedisStreamsClient {
  private client: Redis | null = null;
  private isConnected = false;
  private memoryLog: PublishedEntry[] = [];
  private memorySubscribers: Map<string, Array<(event: CloudEvent) => void>> =
    new Map();

  constructor(private readonly redisUrl?: string) {
    if (this.redisUrl && !this.redisUrl.includes('mock://')) {
      try {
        this.client = new Redis(this.redisUrl, {
          lazyConnect: true,
          retryStrategy: () => null, // Do not hang forever if offline
          maxRetriesPerRequest: 1,
        });
        this.client.connect().then(
          () => {
            this.isConnected = true;
          },
          () => {
            this.isConnected = false;
          }
        );
      } catch {
        this.isConnected = false;
      }
    }
  }

  async publishEvent(stream: string, event: CloudEvent): Promise<string> {
    const id = `${Date.now()}-${this.memoryLog.length}`;
    this.memoryLog.push({ stream, id, event });

    // Notify in-memory subscribers
    const listeners = this.memorySubscribers.get(stream);
    if (listeners) {
      for (const listener of listeners) {
        try {
          listener(event);
        } catch {
          // Ignore subscriber errors
        }
      }
    }

    if (this.client && this.isConnected) {
      try {
        const payload = JSON.stringify(event);
        const result = await this.client.xadd(
          stream,
          '*',
          'event_type',
          event.type,
          'event_id',
          event.id,
          'payload',
          payload
        );
        return result ?? id;
      } catch {
        // Fall back to memory ID
      }
    }
    return id;
  }

  subscribe(
    stream: string,
    callback: (event: CloudEvent) => void
  ): () => void {
    if (!this.memorySubscribers.has(stream)) {
      this.memorySubscribers.set(stream, []);
    }
    this.memorySubscribers.get(stream)!.push(callback);

    return () => {
      const arr = this.memorySubscribers.get(stream) || [];
      const idx = arr.indexOf(callback);
      if (idx !== -1) arr.splice(idx, 1);
    };
  }

  getPublishedEvents(stream?: string): CloudEvent[] {
    if (!stream) {
      return this.memoryLog.map((e) => e.event);
    }
    return this.memoryLog
      .filter((e) => e.stream === stream)
      .map((e) => e.event);
  }

  clearMemory(): void {
    this.memoryLog = [];
  }

  async close(): Promise<void> {
    if (this.client) {
      try {
        await this.client.quit();
      } catch {
        // Ignore disconnect errors
      }
    }
  }
}
