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

test('the JWKS URL is optional and an empty value counts as unset', () => {
  const settings = readZitadelSettings({
    RUNEFOBLE_ZITADEL_ISSUER: 'http://zitadel:8080',
    RUNEFOBLE_ZITADEL_AUDIENCE: 'runefoble-api',
    RUNEFOBLE_ZITADEL_JWKS_URL: '',
  });
  assert.deepEqual(settings, { issuer: 'http://zitadel:8080', audience: 'runefoble-api', jwksUrl: undefined });
});

test('the SpiceDB endpoint has no default and the service refuses to start without it', () => {
  assert.throws(() => readSpicedbEndpoint({}), /RUNEFOBLE_SPICEDB_ENDPOINT/);
  assert.equal(readSpicedbEndpoint({ RUNEFOBLE_SPICEDB_ENDPOINT: 'spicedb:50051' }), 'spicedb:50051');
});
