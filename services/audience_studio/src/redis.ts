/**
 * Redis Streams publisher for Audience Studio (ADR-0006).
 *
 * The client reconnects forever, with backoff capped at five seconds. Commands fail
 * at once while the connection is down, so a request never waits on a dead link.
 */

import { Redis } from 'ioredis';
import { DependencyUnavailableError } from './errors.js';
import type { Logger } from './logger.js';
import type { StreamPublisher } from './streamPublisher.js';
import type { CloudEvent } from './types.js';

const MAX_RECONNECT_DELAY_MS = 5000;

export class RedisStreamsClient implements StreamPublisher {
  private readonly client: Redis;

  constructor(url: string, private readonly log: Logger) {
    this.client = new Redis(url, {
      enableOfflineQueue: false,
      maxRetriesPerRequest: 1,
      retryStrategy: (attempt) => Math.min(100 * 2 ** attempt, MAX_RECONNECT_DELAY_MS),
    });
    this.client.on('error', (err: Error) => {
      this.log.warn({ err }, 'Redis connection error; retrying');
    });
  }

  async publish(stream: string, event: CloudEvent): Promise<string> {
    if (this.client.status !== 'ready') {
      throw new DependencyUnavailableError(`Redis is not connected (stream '${stream}')`);
    }
    let id: string | null;
    try {
      id = await this.client.xadd(
        stream,
        '*',
        'event_type',
        event.type,
        'event_id',
        event.id,
        'payload',
        JSON.stringify(event)
      );
    } catch (err) {
      throw new DependencyUnavailableError(`XADD to '${stream}' failed`, { cause: err });
    }
    if (!id) {
      throw new DependencyUnavailableError(`XADD to '${stream}' returned no entry id`);
    }
    return id;
  }

  async ping(): Promise<boolean> {
    if (this.client.status !== 'ready') return false;
    try {
      return (await this.client.ping()) === 'PONG';
    } catch (err) {
      this.log.warn({ err }, 'Redis ping failed');
      return false;
    }
  }

  async close(): Promise<void> {
    this.client.disconnect();
  }
}
