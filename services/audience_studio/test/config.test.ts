/**
 * Start-up configuration tests. The identity settings have no defaults (ADR-0015 decision c).
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readSpicedbEndpoint, readZitadelSettings } from '../src/config.js';

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
