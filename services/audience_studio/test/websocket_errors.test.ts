/**
 * Frontdoor tests for WebSocket error frames (TASK-0723). Real sockets connect to a listening
 * server. The failing check is a plain Error at the SpiceDB port, the way a driver fault would
 * surface. The client must see a fixed code and no internal text.
 */

import assert from 'node:assert/strict';
import type { AddressInfo } from 'node:net';
import { after, before, describe, test } from 'node:test';
import type { AppContext } from '../src/server.js';
import type { PermissionQuery } from '../src/spicedb/spicedbPort.js';
import { FakeSpiceDb } from './fakeSpiceDb.js';
import { startService, TestIssuer } from './helpers.js';

const API = '/api/v1/audience';
const INTERNAL_DETAIL = 'redis ECONNREFUSED 10.0.0.5:6379 password=hunter2';

/** A SpiceDB fake that can be told to fail every check with an internal driver error. */
class FlakySpiceDb extends FakeSpiceDb {
  failChecks = false;

  override async checkPermission(query: PermissionQuery): Promise<boolean> {
    if (this.failChecks) throw new Error(INTERNAL_DETAIL);
    return super.checkPermission(query);
  }

  override async checkPermissions(queries: PermissionQuery[]): Promise<boolean[]> {
    if (this.failChecks) throw new Error(INTERNAL_DETAIL);
    return super.checkPermissions(queries);
  }
}

let issuer: TestIssuer;
let ctx: AppContext;
let base: string;
let spicedb: FlakySpiceDb;
const sockets: WebSocket[] = [];

before(async () => {
  issuer = await TestIssuer.start();
  spicedb = new FlakySpiceDb();
  ctx = await startService(issuer, { spicedb });
  await ctx.server.listen({ port: 0, host: '127.0.0.1' });
  base = `http://127.0.0.1:${(ctx.server.server.address() as AddressInfo).port}`;
});

after(async () => {
  for (const socket of sockets) socket.close();
  await ctx.server.close();
  await issuer.close();
});

interface Frame {
  type: string;
  code?: string;
  message?: string;
  data?: unknown;
}

/** Opens an authorized socket and returns a reader for the frames it receives. */
async function connect(sub: string, campaignId: string): Promise<{ socket: WebSocket; next(type: string): Promise<Frame> }> {
  const token = await issuer.mint(sub);
  const wsUrl = base.replace('http://', 'ws://');
  const socket = new WebSocket(`${wsUrl}/ws/audience/${campaignId}`, ['runefoble.v1', `runefoble.bearer.${token}`]);
  sockets.push(socket);
  const frames: Frame[] = [];
  const waiters: Array<{ type: string; resolve: (f: Frame) => void }> = [];
  socket.addEventListener('message', (event) => {
    const frame = JSON.parse(String(event.data)) as Frame;
    frames.push(frame);
    for (const waiter of [...waiters]) {
      if (waiter.type === frame.type) {
        waiters.splice(waiters.indexOf(waiter), 1);
        waiter.resolve(frame);
      }
    }
  });
  await new Promise<void>((resolve, reject) => {
    socket.addEventListener('open', () => resolve());
    socket.addEventListener('error', () => reject(new Error(`socket for ${sub} failed to open`)));
  });
  const next = (type: string): Promise<Frame> => {
    const seen = frames.find((f) => f.type === type);
    if (seen) return Promise.resolve(seen);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`no ${type} for ${sub}`)), 3000);
      waiters.push({ type, resolve: (f) => { clearTimeout(timer); resolve(f); } });
    });
  };
  await next('connected');
  return { socket, next };
}

async function createPoll(dm: string, campaignId: string): Promise<string> {
  const res = await fetch(`${base}${API}/polls`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${await issuer.mint(dm)}` },
    body: JSON.stringify({ campaign_id: campaignId, title: 'Errors', prompt: 'Pick', options: ['A'], quorum: 1 }),
  });
  assert.equal(res.status, 201);
  return ((await res.json()) as { id: string }).id;
}

describe('WebSocket error frames', () => {
  test('an unknown action gets an unknown_action error frame', async () => {
    const campaignId = 'camp-ws-unknown';
    spicedb.grant(campaignId, 'spectator', 'spec-ws-unknown');
    const spectator = await connect('spec-ws-unknown', campaignId);

    spectator.socket.send(JSON.stringify({ action: 'dance' }));
    const reply = await spectator.next('error');

    assert.equal(reply.code, 'unknown_action');
  });

  test('a message that is not JSON gets an invalid_message error frame and the socket stays open', async () => {
    const campaignId = 'camp-ws-invalid';
    spicedb.grant(campaignId, 'spectator', 'spec-ws-invalid');
    const spectator = await connect('spec-ws-invalid', campaignId);

    spectator.socket.send('not json {');
    const reply = await spectator.next('error');
    assert.equal(reply.code, 'invalid_message');

    spectator.socket.send(JSON.stringify({ action: 'ping' }));
    await spectator.next('pong');
  });

  test('a failed check sends internal_error with no internal text', async () => {
    const campaignId = 'camp-ws-internal';
    spicedb.grant(campaignId, 'dungeon_master', 'dm-ws-internal');
    spicedb.grant(campaignId, 'spectator', 'spec-ws-internal');
    const pollId = await createPoll('dm-ws-internal', campaignId);
    const spectator = await connect('spec-ws-internal', campaignId);

    spicedb.failChecks = true;
    try {
      spectator.socket.send(JSON.stringify({ action: 'cast_vote', pollId, optionId: 'opt_1' }));
      const reply = await spectator.next('error');

      assert.equal(reply.code, 'internal_error');
      assert.doesNotMatch(reply.message ?? '', /redis|hunter2|ECONNREFUSED|10\.0\.0\.5/);
    } finally {
      spicedb.failChecks = false;
    }
  });
});
