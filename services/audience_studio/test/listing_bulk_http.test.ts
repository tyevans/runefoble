/**
 * Frontdoor tests for listings (TASK-0713). A list request over N polls or proposals checks
 * permissions in at most one bulk call to SpiceDB. The fake at the authorization port counts
 * the calls. The list responses are read through the public routes.
 */

import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { bearer, jsonBody, startService, TestIssuer } from './helpers.js';

const API = '/api/v1/audience';
const POLL_COUNT = 4;

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

async function token(sub: string) {
  return bearer(await issuer.mint(sub));
}

/** Creates `count` polls in one campaign, each closed with a quorum vote, so each has a proposal. */
async function seedCampaign(name: string, count: number): Promise<{ campaignId: string; dm: string; spectator: string }> {
  const campaignId = `camp-${name}`;
  const roles = { campaignId, dm: `dm-${name}`, spectator: `spec-${name}` };
  spicedb.grant(campaignId, 'dungeon_master', roles.dm);
  spicedb.grant(campaignId, 'spectator', roles.spectator);
  for (let i = 0; i < count; i++) {
    const created = await ctx.server.inject({
      method: 'POST',
      url: `${API}/polls`,
      headers: await token(roles.dm),
      payload: { campaign_id: campaignId, title: `Hazard ${i}`, prompt: 'Pick one', options: ['A', 'B'], quorum: 1 },
    });
    assert.equal(created.statusCode, 201);
    const pollId = jsonBody(created).id;
    await ctx.server.inject({
      method: 'POST',
      url: `${API}/polls/${pollId}/votes`,
      headers: await token(roles.spectator),
      payload: { option_id: 'opt_1' },
    });
    const closed = await ctx.server.inject({ method: 'POST', url: `${API}/polls/${pollId}/close`, headers: await token(roles.dm) });
    assert.equal(closed.statusCode, 200);
  }
  return roles;
}

/** Runs one request and returns the response with the number of bulk and single permission calls it made. */
async function countedGet(sub: string, url: string) {
  const bulkBefore = spicedb.calls.bulk;
  const singleBefore = spicedb.calls.single;
  const res = await ctx.server.inject({ method: 'GET', url, headers: await token(sub) });
  return {
    res,
    bulk: spicedb.calls.bulk - bulkBefore,
    single: spicedb.calls.single - singleBefore,
  };
}

describe('a poll listing checks permissions in at most one bulk call', () => {
  test('a DM lists every poll in one bulk call, with proposals and approve on each', async () => {
    const roles = await seedCampaign('poll-list', POLL_COUNT);
    const { res, bulk, single } = await countedGet(roles.dm, `${API}/polls?campaign_id=${roles.campaignId}`);

    assert.equal(res.statusCode, 200);
    assert.equal(jsonBody(res).polls.length, POLL_COUNT);
    assert.ok(bulk <= 1, `expected at most one bulk call, made ${bulk}`);
    assert.equal(single, 0, 'a listing must not check permissions one item at a time');
  });
});

describe('a proposal listing checks permissions in at most one bulk call', () => {
  test('a spectator lists every proposal in one bulk call', async () => {
    const roles = await seedCampaign('proposal-list', POLL_COUNT);
    const { res, bulk, single } = await countedGet(roles.spectator, `${API}/proposals?campaign_id=${roles.campaignId}`);

    assert.equal(res.statusCode, 200);
    assert.equal(jsonBody(res).proposals.length, POLL_COUNT);
    assert.ok(bulk <= 1, `expected at most one bulk call, made ${bulk}`);
    assert.equal(single, 0, 'a listing must not check permissions one item at a time');
  });
});
