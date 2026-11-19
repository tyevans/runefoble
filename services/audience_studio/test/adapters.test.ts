/**
 * Start-up selection of the event store from RUNEFOBLE_EVENT_STORE_BACKEND (ADR-0015 decision f).
 * The same flag name is used by every aggregate-owning service and the Helm gate.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAdapters } from '../src/adapters.js';
import type { Logger } from '../src/logger.js';

const logger: Logger = { info() {}, warn() {}, error() {} };

const DATABASE_URL = 'postgresql://runefoble:secret@127.0.0.1:1/runefoble';

test('the flag selects PostgreSQL when a database URL is set', async () => {
  const adapters = await createAdapters(
    {
      NODE_ENV: 'test',
      RUNEFOBLE_REDIS_URL: 'mock://streams',
      RUNEFOBLE_EVENT_STORE_BACKEND: 'postgresql',
      RUNEFOBLE_DATABASE_URL: DATABASE_URL,
    },
    logger
  );
  assert.equal(adapters.eventStore.kind, 'postgresql');
});

test('the flag set to postgresql fails at start-up without a database URL', async () => {
  await assert.rejects(
    createAdapters({ NODE_ENV: 'test', RUNEFOBLE_EVENT_STORE_BACKEND: 'postgresql' }, logger),
    /RUNEFOBLE_DATABASE_URL is not set/
  );
});

test('a deployed process refuses the memory backend', async () => {
  await assert.rejects(
    createAdapters(
      { NODE_ENV: 'production', RUNEFOBLE_EVENT_STORE_BACKEND: 'memory', RUNEFOBLE_DATABASE_URL: DATABASE_URL },
      logger
    ),
    /RUNEFOBLE_EVENT_STORE_BACKEND=memory is allowed only when NODE_ENV=test/
  );
});

test('the test process selects the memory backend when the flag asks for it', async () => {
  const adapters = await createAdapters({ NODE_ENV: 'test', RUNEFOBLE_EVENT_STORE_BACKEND: 'memory' }, logger);
  assert.equal(adapters.eventStore.kind, 'memory');
});

test('an unknown backend name fails at start-up', async () => {
  await assert.rejects(
    createAdapters({ NODE_ENV: 'test', RUNEFOBLE_EVENT_STORE_BACKEND: 'sqlite' }, logger),
    /must be "postgresql" or "memory"/
  );
});

test('a deployed process with only REDIS_URL set fails at start-up and names RUNEFOBLE_REDIS_URL', async () => {
  await assert.rejects(
    createAdapters(
      { NODE_ENV: 'production', RUNEFOBLE_DATABASE_URL: DATABASE_URL, REDIS_URL: 'redis://127.0.0.1:1/0' },
      logger
    ),
    /RUNEFOBLE_REDIS_URL is not set/
  );
});
