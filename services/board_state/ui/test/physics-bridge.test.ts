import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { PhysicsBridge } from '../src/physics_3d/physics_bridge.ts';

function stub() {
  const calls: { url: string; headers: Record<string, string> }[] = [];
  const fetchImpl = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), headers: init?.headers as Record<string, string> });
    return new Response(JSON.stringify({}), { status: 200 });
  }) as typeof fetch;
  return { calls, fetchImpl };
}

const host = { dispatchEvent: () => true };

describe('PhysicsBridge auth', () => {
  it('sends the bearer on the dice throw and the knockback', async () => {
    const { calls, fetchImpl } = stub();
    const bridge = new PhysicsBridge(host, null, async () => ({ Authorization: 'Bearer tok' }), fetchImpl);

    await bridge.triggerSimulateThrow('board-1');
    await bridge.triggerKnockback('board-1', 'valeros', 1, 0);

    assert.equal(calls.length, 2);
    for (const call of calls) assert.equal(call.headers.Authorization, 'Bearer tok');
    assert.match(calls[0].url, /physics\/simulate-throw$/);
    assert.match(calls[1].url, /physics\/knockback$/);
  });

  it('sends no Authorization header when nobody is signed in', async () => {
    const { calls, fetchImpl } = stub();
    const bridge = new PhysicsBridge(host, null, undefined, fetchImpl);

    await bridge.triggerKnockback('board-1', 'valeros', 1, 0);

    assert.equal('Authorization' in calls[0].headers, false);
  });
});
