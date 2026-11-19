/**
 * Startup configuration for identity and SpiceDB (TASK-0533, TASK-0554, TASK-0625).
 *
 * Neither value has a default. A missing value stops the service at start-up.
 */

import type { ZitadelSettings } from './identity/zitadelVerifier.js';

export const SPICEDB_PRESHARED_KEY_VAR = 'RUNEFOBLE_SPICEDB_PRESHARED_KEY';
export const SPICEDB_ENDPOINT_VAR = 'RUNEFOBLE_SPICEDB_ENDPOINT';

/**
 * Read the SpiceDB endpoint. It has no default. Without it, every permission check would fail,
 * so the service refuses to start (TASK-0554).
 */
export function readSpicedbEndpoint(env: NodeJS.ProcessEnv): string {
  const endpoint = env[SPICEDB_ENDPOINT_VAR];
  if (!endpoint) {
    throw new Error(`${SPICEDB_ENDPOINT_VAR} is not set. The service cannot check audience permissions without it.`);
  }
  return endpoint;
}

/**
 * Read the SpiceDB preshared key from the environment.
 *
 * Throws at startup when the key is missing, unless NODE_ENV is "test". In test mode
 * the key may be empty, because tests do not reach a live SpiceDB.
 */
export function readSpicedbPresharedKey(env: NodeJS.ProcessEnv): string {
  const key = env[SPICEDB_PRESHARED_KEY_VAR];
  if (key) {
    return key;
  }
  if (env.NODE_ENV === 'test') {
    return '';
  }
  throw new Error(
    `${SPICEDB_PRESHARED_KEY_VAR} is not set. The SpiceDB preshared key is an operator secret and has no default.`
  );
}

/**
 * Read the Zitadel verification settings. The issuer and audience are required.
 * The internal URL is optional. Set it when the issuer host is not resolvable from the pod.
 */
export function readZitadelSettings(env: NodeJS.ProcessEnv): ZitadelSettings {
  const issuer = env.RUNEFOBLE_ZITADEL_ISSUER;
  const audience = env.RUNEFOBLE_ZITADEL_AUDIENCE;
  if (!issuer) {
    throw new Error('RUNEFOBLE_ZITADEL_ISSUER is not set. The service cannot verify tokens without it.');
  }
  if (!audience) {
    throw new Error('RUNEFOBLE_ZITADEL_AUDIENCE is not set. The service cannot verify tokens without it.');
  }
  const internalUrl = env.RUNEFOBLE_ZITADEL_INTERNAL_URL || undefined;
  return { issuer, audience, internalUrl };
}

export const DATABASE_URL_VAR = 'RUNEFOBLE_DATABASE_URL';
export const REDIS_URL_VAR = 'RUNEFOBLE_REDIS_URL';
/** Same flag name as the Python services and the Helm gate (scripts/check_helm_event_store.py). */
export const EVENT_STORE_BACKEND_VAR = 'RUNEFOBLE_EVENT_STORE_BACKEND';

/** Where the event store and the stream bus live. Both are required in every environment. */
export interface StoreSettings {
  databaseUrl: string;
  redisUrl: string;
}

/**
 * Read the PostgreSQL and Redis URLs (ADR-0015 decision f). No value has a default, and NODE_ENV
 * changes nothing. Production code has no in-memory store and no mock stream bus. Tests inject
 * fakes through `createAdapters` in `buildServer`.
 */
export function readStoreSettings(env: NodeJS.ProcessEnv): StoreSettings {
  const backend = env[EVENT_STORE_BACKEND_VAR];
  if (backend !== undefined && backend !== 'postgresql') {
    throw new Error(
      `${EVENT_STORE_BACKEND_VAR} must be "postgresql". Got '${backend}'. Audience Studio has no in-memory event store.`
    );
  }
  const databaseUrl = env[DATABASE_URL_VAR];
  if (!databaseUrl) {
    throw new Error(`${DATABASE_URL_VAR} is not set. Audience Studio needs the PostgreSQL event store.`);
  }
  const redisUrl = env[REDIS_URL_VAR];
  if (!redisUrl) {
    throw new Error(`${REDIS_URL_VAR} is not set. Audience Studio needs Redis Streams.`);
  }
  if (!redisUrl.startsWith('redis://') && !redisUrl.startsWith('rediss://')) {
    throw new Error(`${REDIS_URL_VAR} must start with redis:// or rediss://. Got '${redisUrl}'.`);
  }
  return { databaseUrl, redisUrl };
}
