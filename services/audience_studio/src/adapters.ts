/**
 * Selects the event store and stream publisher for this process.
 *
 * Deployed processes need PostgreSQL and a real Redis URL (ADR-0015 decision f). The in-memory
 * store and the mock stream bus are allowed only when NODE_ENV is "test". Anything else fails
 * at start-up.
 */

import { InMemoryStreamPublisher } from './memoryStreams.js';
import { MemoryEventStore } from './eventStore/memoryEventStore.js';
import { PostgresEventStore } from './eventStore/postgresEventStore.js';
import type { EventStore } from './eventStore/types.js';
import type { Logger } from './logger.js';
import { RedisStreamsClient } from './redis.js';
import type { StreamPublisher } from './streamPublisher.js';

export interface Adapters {
  eventStore: EventStore;
  streamPublisher: StreamPublisher;
}

export const DATABASE_URL_VAR = 'RUNEFOBLE_DATABASE_URL';
/** Same flag name as the Python services and the Helm gate (scripts/check_helm_event_store.py). */
export const EVENT_STORE_BACKEND_VAR = 'RUNEFOBLE_EVENT_STORE_BACKEND';

export async function createAdapters(env: NodeJS.ProcessEnv, log: Logger): Promise<Adapters> {
  const isTest = env.NODE_ENV === 'test';
  return {
    eventStore: createEventStore(env, isTest),
    streamPublisher: createStreamPublisher(env, isTest, log),
  };
}

/**
 * Choose the store. An explicit flag wins. "memory" is refused outside tests. Without a flag, a
 * database URL selects PostgreSQL, and tests fall back to memory.
 */
function createEventStore(env: NodeJS.ProcessEnv, isTest: boolean): EventStore {
  const backend = env[EVENT_STORE_BACKEND_VAR];
  const databaseUrl = env[DATABASE_URL_VAR];
  if (backend === 'memory') {
    if (!isTest) {
      throw new Error(`${EVENT_STORE_BACKEND_VAR}=memory is allowed only when NODE_ENV=test. Deployed processes need PostgreSQL.`);
    }
    return new MemoryEventStore();
  }
  if (backend !== undefined && backend !== 'postgresql') {
    throw new Error(`${EVENT_STORE_BACKEND_VAR} must be "postgresql" or "memory". Got '${backend}'.`);
  }
  if (databaseUrl) {
    return new PostgresEventStore(normalizePostgresUrl(databaseUrl));
  }
  if (backend === 'postgresql') {
    throw new Error(`${DATABASE_URL_VAR} is not set. ${EVENT_STORE_BACKEND_VAR}=postgresql needs a database URL.`);
  }
  if (isTest) {
    return new MemoryEventStore();
  }
  throw new Error(`${DATABASE_URL_VAR} is not set. Audience Studio needs the PostgreSQL event store outside tests.`);
}

function createStreamPublisher(env: NodeJS.ProcessEnv, isTest: boolean, log: Logger): StreamPublisher {
  const redisUrl = env.REDIS_URL || env.RUNEFOBLE_REDIS_URL;
  if (!redisUrl) {
    if (isTest) return new InMemoryStreamPublisher();
    throw new Error('REDIS_URL (or RUNEFOBLE_REDIS_URL) is not set. Audience Studio needs Redis Streams outside tests.');
  }
  if (redisUrl.startsWith('mock://')) {
    if (!isTest) {
      throw new Error('mock:// stream URLs are allowed only when NODE_ENV=test');
    }
    return new InMemoryStreamPublisher();
  }
  return new RedisStreamsClient(redisUrl, log);
}

/** The Python services use the SQLAlchemy dialect. The pg driver needs the plain scheme. */
export function normalizePostgresUrl(url: string): string {
  return url.replace(/^postgresql\+asyncpg:\/\//, 'postgresql://');
}
