/**
 * Unit tests for the fail-loud e2e guards (TASK-0650).
 * Run with `node --test e2e/unit/*.test.ts` (Node strips the types). `make test-bdd` runs them.
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  assertOk,
  exactText,
  fillRouteTemplate,
  requireValue,
  type SetupResponse,
} from '../support/guards.ts';

function reply(status: number, body: string): SetupResponse {
  return {
    ok: () => status >= 200 && status < 300,
    status: () => status,
    statusText: () => (status === 503 ? 'Service Unavailable' : 'OK'),
    text: async () => body,
  };
}

test('assertOk throws with the status and the body when the setup response is not OK', async () => {
  await assert.rejects(
    assertOk(reply(503, '{"detail":"character_sheet unavailable"}'), 'Create character'),
    /Create character failed: 503 Service Unavailable - \{"detail":"character_sheet unavailable"\}/
  );
});

test('assertOk returns when the setup response is OK', async () => {
  await assertOk(reply(201, '{}'), 'Create character');
});

test('requireValue throws when the setup value is missing', () => {
  assert.throws(() => requireValue(null, 'No campaign id.'), /No campaign id\./);
  assert.throws(() => requireValue(undefined, 'No character id.'), /No character id\./);
  assert.throws(() => requireValue('', 'Empty id.'), /Empty id\./);
});

test('requireValue returns the value that setup stored', () => {
  assert.equal(requireValue('camp-7', 'No campaign id.'), 'camp-7');
});

test('fillRouteTemplate puts the ids that setup stored into the route', () => {
  assert.equal(
    fillRouteTemplate('#/campaigns/{campaignId}/sessions/{sessionId}', {
      campaignId: 'c-1',
      sessionId: 's-2',
    }),
    '#/campaigns/c-1/sessions/s-2'
  );
});

test('fillRouteTemplate refuses a placeholder that setup did not store', () => {
  assert.throws(
    () => fillRouteTemplate('#/campaigns/{campaignId}/sessions/{sessionId}', { campaignId: 'c-1', sessionId: null }),
    /Route "#\/campaigns\/\{campaignId\}\/sessions\/\{sessionId\}" needs "sessionId", which setup did not store\./
  );
  assert.throws(() => fillRouteTemplate('#/campaigns/{campaignTitle}', { campaignId: 'c-1' }), /needs "campaignTitle"/);
});

test('exactText matches only the whole label', () => {
  assert.ok(exactText('2,2').test(' 2,2 '));
  assert.ok(!exactText('2,2').test('12,2'));
  assert.ok(!exactText('Avoid Melee').test('Avoid Melee Strictly'));
});
