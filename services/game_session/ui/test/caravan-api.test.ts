/**
 * Unit tests for the caravan request client. TASK-0677, TASK-0812.
 *
 * Only the network boundary is replaced (globalThis.fetch). The client code
 * under test runs unchanged. Every request must carry the shared bearer and
 * no caller-asserted identity header (TASK-0812).
 */

import { afterEach, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { apiAcceptContract, apiDispatchCaravan, apiFulfillContract } from '../src/caravan/caravan_api.ts';
import type { CaravanApiContext } from '../src/caravan/caravan_api.ts';
import type { CaravanContractItem } from '../src/runefoble-caravan-types.ts';

const ctx: CaravanApiContext = {
  apiBase: '/api/v1',
  sharedWorldId: 'world-1',
  campaignId: 'camp-1',
  partyName: 'The Amber Vanguard',
  authHeaders: async () => ({ Authorization: 'Bearer caravan-token' }),
};

function makeContract(status: CaravanContractItem['status']): CaravanContractItem {
  return {
    contract_id: 'contract-7',
    origin_outpost: 'Bastion Cross',
    destination_outpost: 'Ironford',
    cargo: { timber: 20 },
    cargo_value: 300,
    route_risk_level: 'medium',
    transit_stages: 3,
    current_stage: 1,
    escort_collateral: 50,
    reward_gold: 150,
    reward_reputation: 15,
    status,
  } as CaravanContractItem;
}

const realFetch = globalThis.fetch;
let requests: { url: string; method: string; headers: Record<string, string> }[] = [];

function stubFetch(handler: () => Response | Promise<Response>): void {
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    requests.push({
      url: String(input),
      method: init?.method ?? 'GET',
      headers: { ...(init?.headers as Record<string, string>) },
    });
    return handler();
  }) as typeof fetch;
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  requests = [];
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe('caravan requests send the shared bearer (TASK-0812)', () => {
  it('sends Authorization on dispatch and no x-user-id header', async () => {
    stubFetch(() => jsonResponse(200, {}));

    await apiDispatchCaravan(ctx, makeContract('accepted'));

    assert.equal(requests[0].headers.Authorization, 'Bearer caravan-token');
    assert.equal('x-user-id' in requests[0].headers, false);
  });

  it('sends Authorization on fulfil', async () => {
    stubFetch(() => jsonResponse(200, {}));

    await apiFulfillContract(ctx, makeContract('in_transit'));

    assert.equal(requests[0].headers.Authorization, 'Bearer caravan-token');
  });

  it('sends Authorization on accept', async () => {
    stubFetch(() => jsonResponse(200, { contract: { status: 'accepted', contractor_party_name: 'The Amber Vanguard' } }));

    await apiAcceptContract(ctx, makeContract('open'));

    assert.equal(requests[0].headers.Authorization, 'Bearer caravan-token');
    assert.equal('x-user-id' in requests[0].headers, false);
  });

  it('sends no Authorization header when the auth source has no token', async () => {
    stubFetch(() => jsonResponse(200, {}));
    const anonymous = { ...ctx, authHeaders: async () => ({}) };

    await apiDispatchCaravan(anonymous, makeContract('accepted'));

    assert.equal('Authorization' in requests[0].headers, false);
  });

  it('shows a sign-in message on 401 and leaves the contract unchanged', async () => {
    stubFetch(() => jsonResponse(401, { detail: 'Not authenticated' }));
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Sign in to continue with this caravan action.' });
    assert.equal(contract.status, 'accepted');
  });

  it('shows a permission message on 403 for accept', async () => {
    stubFetch(() => jsonResponse(403, { detail: 'Forbidden' }));

    await assert.rejects(apiAcceptContract(ctx, makeContract('open')), (err: unknown) => {
      assert.ok(err instanceof Error);
      assert.equal(err.message, 'Your account does not have permission for this caravan action.');
      return true;
    });
  });
});

describe('apiDispatchCaravan', () => {
  it('posts to the dispatch route and marks the contract in transit on 200', async () => {
    stubFetch(() => jsonResponse(200, {}));
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: true });
    assert.equal(requests.length, 1);
    assert.equal(requests[0].method, 'POST');
    assert.equal(
      requests[0].url,
      '/api/v1/shared-worlds/world-1/caravans/contracts/contract-7/dispatch'
    );
    assert.equal(contract.status, 'in_transit');
    assert.equal(contract.current_stage, 1);
  });

  it('returns the server detail and leaves the contract accepted on 503', async () => {
    stubFetch(() => jsonResponse(503, { detail: 'Caravan route service is unavailable.' }));
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Caravan route service is unavailable.' });
    assert.equal(contract.status, 'accepted');
    assert.equal(contract.current_stage, 1);
  });

  it('reports the status code when an error body has no detail', async () => {
    stubFetch(() => new Response('<html>bad gateway</html>', { status: 502 }));
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Request failed with status 502' });
    assert.equal(contract.status, 'accepted');
  });

  it('reports a network error and leaves the contract accepted', async () => {
    stubFetch(() => {
      throw new TypeError('Failed to fetch');
    });
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Network error: Failed to fetch' });
    assert.equal(contract.status, 'accepted');
  });
});

describe('apiFulfillContract', () => {
  it('posts to the fulfil route and marks the contract fulfilled on 200', async () => {
    stubFetch(() => jsonResponse(200, {}));
    const contract = makeContract('in_transit');

    const result = await apiFulfillContract(ctx, contract);

    assert.deepEqual(result, { ok: true });
    assert.equal(
      requests[0].url,
      '/api/v1/shared-worlds/world-1/caravans/contracts/contract-7/fulfill'
    );
    assert.equal(contract.status, 'fulfilled');
    assert.equal(contract.current_stage, contract.transit_stages);
  });

  it('returns the server detail and leaves the contract in transit on 503', async () => {
    stubFetch(() => jsonResponse(503, { detail: 'Payout ledger is unavailable.' }));
    const contract = makeContract('in_transit');
    const stageBefore = contract.current_stage;

    const result = await apiFulfillContract(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Payout ledger is unavailable.' });
    assert.equal(contract.status, 'in_transit');
    assert.equal(contract.current_stage, stageBefore);
  });

  it('reports a network error and leaves the contract in transit', async () => {
    stubFetch(() => {
      throw new TypeError('Failed to fetch');
    });
    const contract = makeContract('in_transit');

    const result = await apiFulfillContract(ctx, contract);

    assert.equal(result.ok, false);
    assert.equal(contract.status, 'in_transit');
  });
});
