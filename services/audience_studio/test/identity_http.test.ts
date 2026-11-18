/**
 * Frontdoor tests for verified identity on HTTP routes (TASK-0533, ADR-0015 decision c).
 * Every request runs through the public HTTP surface with tokens that a Zitadel-like JWKS signs.
 */

import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import {
  bearer,
  jsonBody,
  mintAlgNone,
  mintHs256,
  mintWithForeignKey,
  startService,
  TestIssuer,
} from './helpers.js';

const API = '/api/v1/audience';

let issuer: TestIssuer;
let ctx: AppContext;
let spicedb: FakeSpiceDb;

before(async () => {
  issuer = await TestIssuer.start();
  spicedb = new FakeSpiceDb();
  ctx = await startService(issuer, { spicedb });
});

after(async () => {
  await ctx.server.close();
  await issuer.close();
});

/** Creates a poll as `sub` (a DM of the campaign) and returns its id. Setup goes through the public routes. */
async function createPoll(sub: string, campaignId: string): Promise<string> {
  spicedb.grant(campaignId, 'dungeon_master', sub);
  const res = await ctx.server.inject({
    method: 'POST',
    url: `${API}/polls`,
    headers: bearer(await issuer.mint(sub)),
    payload: { campaign_id: campaignId, title: 'T', prompt: 'P', options: ['A', 'B'], quorum: 1 },
  });
  assert.equal(res.statusCode, 201);
  return jsonBody(res).id;
}

/** Creates a poll, casts one vote, and closes it, so a modifier proposal is pending. */
async function pendingProposal(campaignId: string): Promise<string> {
  const pollId = await createPoll('dm-setup', campaignId);
  spicedb.grant(campaignId, 'spectator', 'viewer-setup');
  await ctx.server.inject({
    method: 'POST',
    url: `${API}/polls/${pollId}/votes`,
    headers: bearer(await issuer.mint('viewer-setup')),
    payload: { option_id: 'opt_1' },
  });
  const closed = jsonBody(
    await ctx.server.inject({
      method: 'POST',
      url: `${API}/polls/${pollId}/close`,
      headers: bearer(await issuer.mint('dm-setup')),
    })
  );
  assert.ok(closed.proposedModifier, 'quorum must produce a proposal');
  return closed.proposedModifier.id;
}

describe('protected routes require a verified bearer token', () => {
  const protectedCalls: Array<{ method: 'GET' | 'POST'; url: string; payload?: object }> = [
    { method: 'GET', url: `${API}/polls` },
    { method: 'POST', url: `${API}/polls`, payload: { campaign_id: 'c', title: 'T', prompt: 'P', options: ['A'] } },
    { method: 'GET', url: `${API}/polls/unknown` },
    { method: 'POST', url: `${API}/polls/unknown/votes`, payload: { option_id: 'opt_1' } },
    { method: 'POST', url: `${API}/polls/unknown/close` },
    { method: 'GET', url: `${API}/proposals` },
    { method: 'POST', url: `${API}/proposals/unknown/approve` },
    { method: 'POST', url: `${API}/proposals/unknown/veto` },
  ];

  test('a request without an Authorization header gets 401 on every protected route', async () => {
    for (const call of protectedCalls) {
      const res = await ctx.server.inject({ method: call.method, url: call.url, payload: call.payload });
      assert.equal(res.statusCode, 401, `${call.method} ${call.url}`);
      assert.equal(res.headers['www-authenticate'], 'Bearer');
    }
  });

  test('forged, expired, mis-scoped, and unsafe tokens get 401', async () => {
    const tokens: Record<string, string> = {
      'signed by an untrusted key': await mintWithForeignKey('mallory'),
      'HS256 with a shared secret': await mintHs256('mallory'),
      'alg none': mintAlgNone('mallory'),
      expired: await issuer.mint('mallory', { expiresInSeconds: -120 }),
      'wrong audience': await issuer.mint('mallory', { audience: 'some-other-api' }),
      'wrong issuer': await issuer.mint('mallory', { issuer: 'http://evil.test' }),
      'malformed': 'not-a-jwt',
    };
    for (const [label, token] of Object.entries(tokens)) {
      const res = await ctx.server.inject({
        method: 'GET',
        url: `${API}/polls`,
        headers: bearer(token),
      });
      assert.equal(res.statusCode, 401, label);
    }
  });

  test('a valid token opens a protected route', async () => {
    const res = await ctx.server.inject({
      method: 'GET',
      url: `${API}/polls`,
      headers: bearer(await issuer.mint('viewer-ok')),
    });
    assert.equal(res.statusCode, 200);
  });

  test('an unreachable JWKS endpoint returns 503, not a token rejection', async () => {
    // Keys are fetched on the first verification, so the issuer can go away after start-up.
    const dying = await TestIssuer.start();
    const unreachable = await startService(dying);
    try {
      const token = await dying.mint('viewer-down');
      await dying.close();
      const res = await unreachable.server.inject({
        method: 'GET',
        url: `${API}/polls`,
        headers: bearer(token),
      });
      assert.equal(res.statusCode, 503);
    } finally {
      await unreachable.server.close();
    }
  });
});

describe('public operational routes need no token', () => {
  test('health, readiness, and the microfrontend manifest answer without a token', async () => {
    for (const url of ['/healthz', '/readyz', '/ui/manifest']) {
      const res = await ctx.server.inject({ method: 'GET', url });
      assert.equal(res.statusCode, 200, url);
    }
  });
});

describe('the actor is the token subject', () => {
  test('the removed tuple route returns 404 for a valid token', async () => {
    const res = await ctx.server.inject({
      method: 'POST',
      url: `${API}/auth/tuples`,
      headers: bearer(await issuer.mint('mallory')),
      payload: {
        resource_type: 'campaign',
        resource_id: 'camp-tuple',
        relation: 'dungeon_master',
        subject_type: 'user',
        subject_id: 'mallory',
      },
    });
    assert.equal(res.statusCode, 404);
  });

  test('approve with a non-DM token returns 403 even when the body names a DM', async () => {
    const proposalId = await pendingProposal('camp-approve');
    const res = await ctx.server.inject({
      method: 'POST',
      url: `${API}/proposals/${proposalId}/approve`,
      headers: { ...bearer(await issuer.mint('mallory')), 'x-user-id': 'dm-alice' },
      payload: { dm_user_id: 'dm-alice' },
    });
    assert.equal(res.statusCode, 403);
    assert.doesNotMatch(jsonBody(res).error, /dm-alice/);
  });

  test('veto with a non-DM token returns 403 and the proposal stays pending', async () => {
    const proposalId = await pendingProposal('camp-veto');
    const res = await ctx.server.inject({
      method: 'POST',
      url: `${API}/proposals/${proposalId}/veto`,
      headers: bearer(await issuer.mint('mallory')),
    });
    assert.equal(res.statusCode, 403);
    const pending = jsonBody(
      await ctx.server.inject({
        method: 'GET',
        url: `${API}/proposals?campaign_id=camp-veto&status=pending`,
        headers: bearer(await issuer.mint('dm-setup')),
      })
    );
    assert.equal(pending.proposals.length, 1);
  });

  test('a vote is recorded for the token subject, not the body voter_id', async () => {
    const pollId = await createPoll('dm-vote', 'camp-vote');
    spicedb.grant('camp-vote', 'spectator', 'viewer-real');
    const first = await ctx.server.inject({
      method: 'POST',
      url: `${API}/polls/${pollId}/votes`,
      headers: bearer(await issuer.mint('viewer-real')),
      payload: { voter_id: 'viewer-spoofed', option_id: 'opt_1' },
    });
    assert.equal(first.statusCode, 200);
    const second = await ctx.server.inject({
      method: 'POST',
      url: `${API}/polls/${pollId}/votes`,
      headers: bearer(await issuer.mint('viewer-real')),
      payload: { option_id: 'opt_2' },
    });
    assert.equal(second.statusCode, 400);
    assert.match(jsonBody(second).error, /already voted/);
  });
});
