/**
 * Frontdoor tests for schema-based object authorization on the HTTP routes (TASK-0554).
 * Each role is a relation on the campaign, written into the fake SpiceDB at the authorization
 * port. Requests run through the public routes. Assertions read responses only.
 */

import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { bearer, jsonBody, startService, TestIssuer } from './helpers.js';

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

/** Grants one DM, one spectator, one player, and returns the campaign id. Each test uses its own campaign. */
function campaignWithRoles(name: string): { campaignId: string; dm: string; spectator: string; player: string } {
  const campaignId = `camp-${name}`;
  const roles = { campaignId, dm: `dm-${name}`, spectator: `spec-${name}`, player: `play-${name}` };
  spicedb.grant(campaignId, 'dungeon_master', roles.dm);
  spicedb.grant(campaignId, 'spectator', roles.spectator);
  spicedb.grant(campaignId, 'player', roles.player);
  return roles;
}

async function token(sub: string): Promise<{ authorization: string }> {
  return bearer(await issuer.mint(sub));
}

async function createPoll(sub: string, campaignId: string): Promise<{ status: number; body: any }> {
  const res = await ctx.server.inject({
    method: 'POST',
    url: `${API}/polls`,
    headers: await token(sub),
    payload: { campaign_id: campaignId, title: 'Hazard', prompt: 'Pick one', options: ['A', 'B'], quorum: 1 },
  });
  return { status: res.statusCode, body: jsonBody(res) };
}

async function vote(sub: string, pollId: string, body: object = { option_id: 'opt_1' }) {
  return ctx.server.inject({ method: 'POST', url: `${API}/polls/${pollId}/votes`, headers: await token(sub), payload: body });
}

async function closePoll(sub: string, pollId: string) {
  return ctx.server.inject({ method: 'POST', url: `${API}/polls/${pollId}/close`, headers: await token(sub) });
}

/** A DM-created poll with one vote, closed. Returns the poll id and the pending proposal id. */
async function closedPollWithProposal(roles: { campaignId: string; dm: string; spectator: string }) {
  const created = await createPoll(roles.dm, roles.campaignId);
  assert.equal(created.status, 201);
  await vote(roles.spectator, created.body.id);
  const closed = jsonBody(await closePoll(roles.dm, created.body.id));
  assert.ok(closed.proposedModifier, 'quorum must produce a proposal');
  return { pollId: created.body.id as string, proposalId: closed.proposedModifier.id as string };
}

describe('creating and closing polls needs campaign run_session', () => {
  test('a stranger cannot create a poll, and a DM can', async () => {
    const roles = campaignWithRoles('create');
    const denied = await createPoll('stranger-create', roles.campaignId);
    assert.equal(denied.status, 403);
    const allowed = await createPoll(roles.dm, roles.campaignId);
    assert.equal(allowed.status, 201);
  });

  test('a spectator cannot close a poll, and a DM can', async () => {
    const roles = campaignWithRoles('close');
    const created = await createPoll(roles.dm, roles.campaignId);
    assert.equal((await closePoll(roles.spectator, created.body.id)).statusCode, 403);
    assert.equal((await closePoll(roles.dm, created.body.id)).statusCode, 200);
  });
});

describe('reading polls needs audience_poll.view', () => {
  test('a stranger gets 403 for one poll and an empty list, a spectator reads both', async () => {
    const roles = campaignWithRoles('read');
    const created = await createPoll(roles.dm, roles.campaignId);

    const one = await ctx.server.inject({ method: 'GET', url: `${API}/polls/${created.body.id}`, headers: await token('stranger-read') });
    assert.equal(one.statusCode, 403);

    const strangerList = jsonBody(await ctx.server.inject({ method: 'GET', url: `${API}/polls?campaign_id=${roles.campaignId}`, headers: await token('stranger-read') }));
    assert.deepEqual(strangerList.polls, []);

    const spectatorOne = await ctx.server.inject({ method: 'GET', url: `${API}/polls/${created.body.id}`, headers: await token(roles.spectator) });
    assert.equal(spectatorOne.statusCode, 200);
    const spectatorList = jsonBody(await ctx.server.inject({ method: 'GET', url: `${API}/polls?campaign_id=${roles.campaignId}`, headers: await token(roles.spectator) }));
    assert.equal(spectatorList.polls.length, 1);
  });

  test('an unknown poll is 404 for a caller who has every role', async () => {
    const roles = campaignWithRoles('missing');
    const res = await ctx.server.inject({ method: 'GET', url: `${API}/polls/no-such-poll`, headers: await token(roles.dm) });
    assert.equal(res.statusCode, 404);
  });
});

describe('votes need audience_poll.vote and use the token subject', () => {
  test('a stranger cannot vote, and a spectator vote changes the poll', async () => {
    const roles = campaignWithRoles('vote');
    const created = await createPoll(roles.dm, roles.campaignId);

    assert.equal((await vote('stranger-vote', created.body.id)).statusCode, 403);
    const ok = await vote(roles.spectator, created.body.id);
    assert.equal(ok.statusCode, 200);
    assert.equal(jsonBody(ok).poll.totalVotes, 1);
  });

  test('a player who names a different voter_id still casts one ballot as themselves', async () => {
    const roles = campaignWithRoles('dedupe');
    const created = await createPoll(roles.dm, roles.campaignId);
    assert.equal((await vote(roles.player, created.body.id, { voter_id: 'someone-else', option_id: 'opt_1' })).statusCode, 200);
    const second = await vote(roles.player, created.body.id, { voter_id: 'someone-else-again', option_id: 'opt_2' });
    assert.equal(second.statusCode, 400);
    assert.match(jsonBody(second).error, /already voted/);
  });
});

describe('proposal parameters are visible only with audience_poll.approve', () => {
  test('a spectator sees the proposal title and status, and no parameters', async () => {
    const roles = campaignWithRoles('params');
    const { pollId, proposalId } = await closedPollWithProposal(roles);

    const spectatorList = jsonBody(
      await ctx.server.inject({ method: 'GET', url: `${API}/proposals?campaign_id=${roles.campaignId}`, headers: await token(roles.spectator) })
    );
    const [summary] = spectatorList.proposals;
    assert.equal(summary.id, proposalId);
    assert.equal(summary.status, 'pending');
    assert.ok(summary.title);
    assert.equal(summary.parameters, undefined);
    assert.equal(summary.description, undefined);

    const spectatorPoll = jsonBody(await ctx.server.inject({ method: 'GET', url: `${API}/polls/${pollId}`, headers: await token(roles.spectator) }));
    assert.equal(spectatorPoll.proposedModifier.parameters, undefined);

    const dmList = jsonBody(
      await ctx.server.inject({ method: 'GET', url: `${API}/proposals?campaign_id=${roles.campaignId}`, headers: await token(roles.dm) })
    );
    assert.ok(dmList.proposals[0].parameters, 'the DM sees parameters');
  });

  test('a stranger sees no proposals at all', async () => {
    const roles = campaignWithRoles('hidden');
    await closedPollWithProposal(roles);
    const list = jsonBody(
      await ctx.server.inject({ method: 'GET', url: `${API}/proposals?campaign_id=${roles.campaignId}`, headers: await token('stranger-hidden') })
    );
    assert.deepEqual(list.proposals, []);
  });
});

describe('approve and veto need audience_poll.approve and audience_poll.veto', () => {
  test('a spectator and a player cannot approve, and the DM can', async () => {
    const roles = campaignWithRoles('approve');
    const { proposalId } = await closedPollWithProposal(roles);

    for (const sub of [roles.spectator, roles.player, 'stranger-approve']) {
      const res = await ctx.server.inject({ method: 'POST', url: `${API}/proposals/${proposalId}/approve`, headers: await token(sub) });
      assert.equal(res.statusCode, 403, sub);
    }
    const approved = await ctx.server.inject({ method: 'POST', url: `${API}/proposals/${proposalId}/approve`, headers: await token(roles.dm) });
    assert.equal(approved.statusCode, 200);
    assert.equal(jsonBody(approved).proposal.status, 'approved');
    assert.equal(jsonBody(approved).proposal.reviewedBy, roles.dm);
  });

  test('a spectator cannot veto, and the proposal stays pending', async () => {
    const roles = campaignWithRoles('veto');
    const { proposalId } = await closedPollWithProposal(roles);
    const denied = await ctx.server.inject({ method: 'POST', url: `${API}/proposals/${proposalId}/veto`, headers: await token(roles.spectator) });
    assert.equal(denied.statusCode, 403);
    const pending = jsonBody(
      await ctx.server.inject({ method: 'GET', url: `${API}/proposals?campaign_id=${roles.campaignId}&status=pending`, headers: await token(roles.dm) })
    );
    assert.equal(pending.proposals.length, 1);
  });

  test('an unknown proposal is 404, not 400 and not a text match', async () => {
    const roles = campaignWithRoles('unknown-proposal');
    const res = await ctx.server.inject({ method: 'POST', url: `${API}/proposals/no-such/approve`, headers: await token(roles.dm) });
    assert.equal(res.statusCode, 404);
  });
});

describe('an unreachable SpiceDB fails closed with 503', () => {
  test('reads and decisions return 503 during an outage and recover after it', async () => {
    const roles = campaignWithRoles('outage');
    const { pollId, proposalId } = await closedPollWithProposal(roles);

    spicedb.setUnavailable(true);
    try {
      const read = await ctx.server.inject({ method: 'GET', url: `${API}/polls/${pollId}`, headers: await token(roles.dm) });
      assert.equal(read.statusCode, 503);
      const approve = await ctx.server.inject({ method: 'POST', url: `${API}/proposals/${proposalId}/approve`, headers: await token(roles.dm) });
      assert.equal(approve.statusCode, 503);
    } finally {
      spicedb.setUnavailable(false);
    }

    const recovered = await ctx.server.inject({ method: 'GET', url: `${API}/polls/${pollId}`, headers: await token(roles.dm) });
    assert.equal(recovered.statusCode, 200);
  });
});
