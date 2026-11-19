/**
 * Builds the event store and stream publisher for this process (ADR-0015 decision f).
 *
 * Production code builds PostgreSQL and Redis adapters only. Tests inject fakes through the
 * `createAdapters` option of `buildServer`.
 */

import type { StoreSettings } from './config.js';
import { PostgresEventStore } from './eventStore/postgresEventStore.js';
import type { EventStore } from './eventStore/types.js';
import type { Logger } from './logger.js';
import { RedisStreamsClient } from './redis.js';
import type { StreamPublisher } from './streamPublisher.js';

export interface Adapters {
  eventStore: EventStore;
  streamPublisher: StreamPublisher;
}

export async function createAdapters(settings: StoreSettings, log: Logger): Promise<Adapters> {
  return {
    eventStore: new PostgresEventStore(settings.databaseUrl),
    streamPublisher: new RedisStreamsClient(settings.redisUrl, log),
  };
}
