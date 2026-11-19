/**
 * Start-up configuration tests. The identity settings have no defaults (ADR-0015 decision c).
 * The event store and the stream bus have no in-memory choice in production code (ADR-0015 decision f).
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readSpicedbEndpoint, readStoreSettings, readZitadelSettings } from '../src/config.js';

test('the service refuses to start without an issuer or an audience', () => {
  assert.throws(() => readZitadelSettings({ RUNEFOBLE_ZITADEL_AUDIENCE: 'runefoble-api' }), /RUNEFOBLE_ZITADEL_ISSUER/);
  assert.throws(() => readZitadelSettings({ RUNEFOBLE_ZITADEL_ISSUER: 'http://zitadel:8080' }), /RUNEFOBLE_ZITADEL_AUDIENCE/);
});

test('the internal URL is optional and an empty value counts as unset', () => {
  const settings = readZitadelSettings({
    RUNEFOBLE_ZITADEL_ISSUER: 'http://zitadel:8080',
    RUNEFOBLE_ZITADEL_AUDIENCE: 'runefoble-api',
    RUNEFOBLE_ZITADEL_INTERNAL_URL: '',
  });
  assert.deepEqual(settings, { issuer: 'http://zitadel:8080', audience: 'runefoble-api', internalUrl: undefined });
});

test('the internal URL is read when set', () => {
  const settings = readZitadelSettings({
    RUNEFOBLE_ZITADEL_ISSUER: 'http://auth.localhost',
    RUNEFOBLE_ZITADEL_AUDIENCE: 'project-1',
    RUNEFOBLE_ZITADEL_INTERNAL_URL: 'http://zitadel:8080',
  });
  assert.deepEqual(settings, { issuer: 'http://auth.localhost', audience: 'project-1', internalUrl: 'http://zitadel:8080' });
});

test('the SpiceDB endpoint has no default and the service refuses to start without it', () => {
  assert.throws(() => readSpicedbEndpoint({}), /RUNEFOBLE_SPICEDB_ENDPOINT/);
  assert.equal(readSpicedbEndpoint({ RUNEFOBLE_SPICEDB_ENDPOINT: 'spicedb:50051' }), 'spicedb:50051');
});

const DATABASE_URL = 'postgresql://runefoble:secret@127.0.0.1:1/runefoble';
const REDIS_URL = 'redis://127.0.0.1:1/0';

for (const nodeEnv of ['test', 'development', 'production', undefined]) {
  test(`start-up refuses without RUNEFOBLE_DATABASE_URL when NODE_ENV is ${nodeEnv ?? 'unset'}`, () => {
    assert.throws(
      () => readStoreSettings({ NODE_ENV: nodeEnv, RUNEFOBLE_REDIS_URL: REDIS_URL }),
      /RUNEFOBLE_DATABASE_URL is not set/
    );
  });

  test(`start-up refuses without RUNEFOBLE_REDIS_URL when NODE_ENV is ${nodeEnv ?? 'unset'}`, () => {
    assert.throws(
      () => readStoreSettings({ NODE_ENV: nodeEnv, RUNEFOBLE_DATABASE_URL: DATABASE_URL }),
      /RUNEFOBLE_REDIS_URL is not set/
    );
  });
}

test('the store settings carry the PostgreSQL and Redis URLs', () => {
  assert.deepEqual(
    readStoreSettings({ RUNEFOBLE_DATABASE_URL: DATABASE_URL, RUNEFOBLE_REDIS_URL: REDIS_URL }),
    { databaseUrl: DATABASE_URL, redisUrl: REDIS_URL }
  );
});

test('the backend flag accepts postgresql, the Helm value', () => {
  const settings = readStoreSettings({
    RUNEFOBLE_EVENT_STORE_BACKEND: 'postgresql',
    RUNEFOBLE_DATABASE_URL: DATABASE_URL,
    RUNEFOBLE_REDIS_URL: REDIS_URL,
  });
  assert.equal(settings.databaseUrl, DATABASE_URL);
});

test('the memory backend is refused, also when NODE_ENV is test', () => {
  assert.throws(
    () =>
      readStoreSettings({
        NODE_ENV: 'test',
        RUNEFOBLE_EVENT_STORE_BACKEND: 'memory',
        RUNEFOBLE_DATABASE_URL: DATABASE_URL,
        RUNEFOBLE_REDIS_URL: REDIS_URL,
      }),
    /RUNEFOBLE_EVENT_STORE_BACKEND must be "postgresql". Got 'memory'/
  );
});

test('a mock:// stream URL is refused, also when NODE_ENV is test', () => {
  assert.throws(
    () =>
      readStoreSettings({ NODE_ENV: 'test', RUNEFOBLE_DATABASE_URL: DATABASE_URL, RUNEFOBLE_REDIS_URL: 'mock://redis' }),
    /RUNEFOBLE_REDIS_URL must start with redis:\/\/ or rediss:\/\//
  );
});

test('REDIS_URL without the RUNEFOBLE_ prefix is not read', () => {
  assert.throws(
    () => readStoreSettings({ RUNEFOBLE_DATABASE_URL: DATABASE_URL, REDIS_URL }),
    /RUNEFOBLE_REDIS_URL is not set/
  );
});
