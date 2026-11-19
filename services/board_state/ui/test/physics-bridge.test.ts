/**
 * PhysicsBridge transport tests (TASK-0538, TASK-0758).
 * The bridge calls a real HTTP server on the loopback interface. Nothing replaces `fetch`.
 */

import assert from 'node:assert/strict';
import { after, before, beforeEach, describe, it } from 'node:test';
import { HttpError, type AuthSource } from '@runefoble/ui-core';
import { startLoopbackUpstream, type LoopbackUpstream } from '@runefoble/ui-core/testing/loopback-upstream';
import { PhysicsBridge } from '../src/physics_3d/physics_bridge.ts';

const signedIn: AuthSource = { authHeaders: async () => ({ Authorization: 'Bearer tok' }) };

let upstream: LoopbackUpstream;
let host: { apiBaseUrl: string; dispatchEvent: (event: Event) => boolean; events: string[] };

before(async () => {
  upstream = await startLoopbackUpstream();
});

after(() => upstream.close());

beforeEach(() => {
  upstream.reset();
  const events: string[] = [];
  host = { apiBaseUrl: upstream.url, events, dispatchEvent: (event) => (events.push(event.type), true) };
});

describe('PhysicsBridge transport', () => {
  it('sends the bearer on the dice throw and the knockback under the host API base', async () => {
    const bridge = new PhysicsBridge(host, null, signedIn);

    await bridge.triggerSimulateThrow('board-1');
    await bridge.triggerKnockback('board-1', 'valeros', 1, 0);

    assert.equal(upstream.requests.length, 2);
    for (const req of upstream.requests) {
      assert.equal(req.method, 'POST');
      assert.equal(req.headers.authorization, 'Bearer tok');
      assert.equal(req.headers['content-type'], 'application/json');
    }
    assert.equal(upstream.requests[0].path, '/api/v1/boards/board-1/physics/simulate-throw');
    assert.equal(upstream.requests[1].path, '/api/v1/boards/board-1/physics/knockback');
    assert.deepEqual(JSON.parse(upstream.requests[1].body), {
      token_id: 'valeros', direction_x: 1, direction_y: 0, distance_ft: 10, mass: 1,
    });
  });

  it('sends no Authorization header when nobody is signed in', async () => {
    const bridge = new PhysicsBridge(host, null);

    await bridge.triggerKnockback('board-1', 'valeros', 1, 0);

    assert.equal('authorization' in upstream.requests[0].headers, false);
  });

  it('announces the settled dice from the server reply', async () => {
    upstream.reply(200, { dice_id: 'd1', dice_type: 'd20', face_value: 17, settled_cell: [2, 3], trajectory: [] });
    const bridge = new PhysicsBridge(host, null, signedIn);

    const data = await bridge.triggerSimulateThrow('board-1');

    assert.equal(data.face_value, 17);
    assert.deepEqual(host.events, ['dice-settled']);
  });

  it('rejects with HttpError carrying the server detail and announces nothing', async () => {
    upstream.reply(403, { detail: 'Forbidden: only the DM can apply knockback.' });
    const bridge = new PhysicsBridge(host, null, signedIn);

    await assert.rejects(bridge.triggerKnockback('board-1', 'valeros', 1, 0), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.status, 403);
      assert.equal(err.detail, 'Forbidden: only the DM can apply knockback.');
      return true;
    });
    assert.deepEqual(host.events, []);
  });
});
