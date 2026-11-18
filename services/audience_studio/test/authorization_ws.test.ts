/**
 * Frontdoor tests for WebSocket authorization (TASK-0554). Real sockets connect to a listening
 * server. Each socket presents a verified bearer subprotocol. Polls are created and closed over
 * HTTP, so the broadcasts come from the same commands that a client would send.
 */

import assert from 'node:assert/strict';
import type { AddressInfo } from 'node:net';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { startService, TestIssuer } from './helpers.js';

const API = '/api/v1/audience';

let issuer: TestIssuer;
let ctx: AppContext;
let base: string;
let spicedb: FakeSpiceDb;
const sockets: WebSocket[] = [];

before(async () => {
  issuer = await TestIssuer.start();
  spicedb = new FakeSpiceDb();
  ctx = await startService(issuer, { spicedb });
  await ctx.server.listen({ port: 0, host: '127.0.0.1' });
  base = `http://127.0.0.1:${(ctx.server.server.address() as AddressInfo).port}`;
});

after(async () => {
  for (const socket of sockets) socket.close();
  await ctx.server.close();
  await issuer.close();
});

/** Collects every message a socket receives, in order. */
interface Recorder {
  socket: WebSocket;
  messages: Array<{ type: string; data?: any; message?: string }>;
  next(type: string): Promise<{ type: string; data?: any; message?: string }>;
}

async function connect(sub: string, campaignId: string): Promise<Recorder> {
  const token = await issuer.mint(sub);
  const wsUrl = base.replace('http://', 'ws://');
  const socket = new WebSocket(`${wsUrl}/ws/audience/${campaignId}`, ['runefoble.v1', `runefoble.bearer.${token}`]);
  sockets.push(socket);
  const messages: Recorder['messages'] = [];
  const waiters: Array<{ type: string; resolve: (m: (typeof messages)[number]) => void }> = [];
  socket.addEventListener('message', (event) => {
    const msg = JSON.parse(String(event.data));
    messages.push(msg);
    for (const waiter of [...waiters]) {
      if (waiter.type === msg.type) {
        waiters.splice(waiters.indexOf(waiter), 1);
        waiter.resolve(msg);
      }
    }
  });
  await new Promise<void>((resolve, reject) => {
    socket.addEventListener('open', () => resolve());
    socket.addEventListener('error', () => reject(new Error(`socket for ${sub} failed to open`)));
  });
  const recorder: Recorder = {
    socket,
    messages,
    next(type) {
      const seen = messages.find((m) => m.type === type);
      if (seen) return Promise.resolve(seen);
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`no ${type} for ${sub}`)), 3000);
        waiters.push({ type, resolve: (m) => { clearTimeout(timer); resolve(m); } });
      });
    },
  };
  await recorder.next('connected');
  return recorder;
}

async function http(method: 'GET' | 'POST', path: string, sub: string, body?: object): Promise<any> {
  const res = await fetch(`${base}${API}${path}`, {
    method,
    headers: body
      ? { authorization: `Bearer ${await issuer.mint(sub)}`, 'content-type': 'application/json' }
      : { authorization: `Bearer ${await issuer.mint(sub)}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, body: await res.json() };
}

describe('the handshake needs campaign view', () => {
  test('a socket for a campaign the principal cannot view is refused', async () => {
    spicedb.grant('camp-ws-deny', 'spectator', 'someone-ws');
    const token = await issuer.mint('stranger-ws-deny');
    const socket = new WebSocket(`${base.replace('http://', 'ws://')}/ws/audience/camp-ws-deny`, ['runefoble.v1', `runefoble.bearer.${token}`]);
    sockets.push(socket);
    const outcome = await new Promise<'open' | 'refused'>((resolve) => {
      socket.addEventListener('open', () => resolve('open'));
      socket.addEventListener('error', () => resolve('refused'));
      socket.addEventListener('close', () => resolve('refused'));
    });
    assert.equal(outcome, 'refused');
  });
});

describe('broadcasts respect audience_poll.approve', () => {
  test('proposal_queued reaches only DM sockets and carries parameters there', async () => {
    const campaignId = 'camp-ws-fanout';
    spicedb.grant(campaignId, 'dungeon_master', 'dm-ws-fanout');
    spicedb.grant(campaignId, 'spectator', 'spec-ws-fanout');

    const dm = await connect('dm-ws-fanout', campaignId);
    const spectator = await connect('spec-ws-fanout', campaignId);

    const created = await http('POST', '/polls', 'dm-ws-fanout', {
      campaign_id: campaignId, title: 'Fanout', prompt: 'Pick', options: ['A'], quorum: 1,
    });
    assert.equal(created.status, 201);
    await http('POST', `/polls/${created.body.id}/votes`, 'spec-ws-fanout', { option_id: 'opt_1' });
    const closed = await http('POST', `/polls/${created.body.id}/close`, 'dm-ws-fanout');
    assert.equal(closed.status, 200);

    // Events for one campaign are delivered in commit order, so poll_completed arrives after proposal_queued.
    await spectator.next('poll_completed');
    const queuedForDm = await dm.next('proposal_queued');
    assert.ok(queuedForDm.data.parameters, 'the DM sees parameters');
    assert.equal(spectator.messages.some((m) => m.type === 'proposal_queued'), false);
    assert.equal(spectator.messages.some((m) => m.type === 'poll_completed'), true);
  });

  test('a spectator who tries to approve over the socket gets an error and no decision', async () => {
    const campaignId = 'camp-ws-decide';
    spicedb.grant(campaignId, 'dungeon_master', 'dm-ws-decide');
    spicedb.grant(campaignId, 'spectator', 'spec-ws-decide');
    const spectator = await connect('spec-ws-decide', campaignId);

    const created = await http('POST', '/polls', 'dm-ws-decide', {
      campaign_id: campaignId, title: 'Decide', prompt: 'Pick', options: ['A'], quorum: 1,
    });
    await http('POST', `/polls/${created.body.id}/votes`, 'spec-ws-decide', { option_id: 'opt_1' });
    const closed = await http('POST', `/polls/${created.body.id}/close`, 'dm-ws-decide');
    const proposalId = closed.body.proposedModifier.id;

    spectator.socket.send(JSON.stringify({ action: 'approve_proposal', proposalId }));
    const reply = await spectator.next('error');
    assert.match(reply.message ?? '', /Permission 'approve'/);

    const list = await http('GET', `/proposals?campaign_id=${campaignId}`, 'dm-ws-decide');
    assert.equal(list.body.proposals[0].status, 'pending');
  });

  test('a DM socket approves and receives the decision with parameters', async () => {
    const campaignId = 'camp-ws-approve';
    spicedb.grant(campaignId, 'dungeon_master', 'dm-ws-approve');
    spicedb.grant(campaignId, 'spectator', 'spec-ws-approve');
    const dm = await connect('dm-ws-approve', campaignId);

    const created = await http('POST', '/polls', 'dm-ws-approve', {
      campaign_id: campaignId, title: 'Approve', prompt: 'Pick', options: ['A'], quorum: 1,
    });
    await http('POST', `/polls/${created.body.id}/votes`, 'spec-ws-approve', { option_id: 'opt_1' });
    const closed = await http('POST', `/polls/${created.body.id}/close`, 'dm-ws-approve');

    dm.socket.send(JSON.stringify({ action: 'approve_proposal', proposalId: closed.body.proposedModifier.id }));
    const approved = await dm.next('proposal_approved');
    assert.equal(approved.data.status, 'approved');
    assert.equal(approved.data.reviewedBy, 'dm-ws-approve');
  });
});
