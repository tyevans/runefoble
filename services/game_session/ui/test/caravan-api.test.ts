/**
 * Caravan request client over the shared UI transport. TASK-0677, TASK-0812, TASK-0759.
 *
 * The calls go to a real HTTP server on the loopback interface. Nothing replaces `fetch`.
 * Every request must carry the shared bearer and no caller-asserted identity header. A
 * refused request reports distinct text for 401, 403 and 503, and leaves the contract as it was.
 */

import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';

import type { AuthSource } from '@runefoble/ui-core';
import { startLoopbackUpstream, type LoopbackUpstream } from '@runefoble/ui-core/testing/loopback-upstream';
import { apiAcceptContract, apiDispatchCaravan, apiFulfillContract } from '../src/caravan/caravan_api.ts';
import type { CaravanApiContext } from '../src/caravan/caravan_api.ts';
import type { CaravanContractItem } from '../src/runefoble-caravan-types.ts';

const signedIn: AuthSource = { authHeaders: async () => ({ Authorization: 'Bearer caravan-token' }) };
const anonymous: AuthSource = { authHeaders: async () => ({}) };

let upstream: LoopbackUpstream;
let ctx: CaravanApiContext;

before(async () => {
  upstream = await startLoopbackUpstream();
});

after(() => upstream.close());

beforeEach(() => {
  upstream.reset();
  ctx = {
    apiBase: `${upstream.url}/api/v1`,
    sharedWorldId: 'world-1',
    campaignId: 'camp-1',
    partyName: 'The Amber Vanguard',
    auth: signedIn,
  };
});

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

function onlyCall() {
  assert.equal(upstream.requests.length, 1);
  const req = upstream.requests[0];
  return { method: req.method, path: req.path, headers: req.headers, body: req.body ? JSON.parse(req.body) : undefined };
}

describe('caravan requests send the shared bearer and no x-user-id', () => {
  it('sends the bearer on accept, dispatch and fulfil', async () => {
    upstream.reply(200, {});
    await apiAcceptContract(ctx, makeContract('open'));
    await apiDispatchCaravan(ctx, makeContract('accepted'));
    await apiFulfillContract(ctx, makeContract('in_transit'));

    assert.equal(upstream.requests.length, 3);
    for (const req of upstream.requests) {
      assert.equal(req.method, 'POST');
      assert.equal(req.headers.authorization, 'Bearer caravan-token');
      assert.equal('x-user-id' in req.headers, false);
    }
  });

  it('sends no Authorization header when the auth source has no token', async () => {
    upstream.reply(200, {});

    await apiDispatchCaravan({ ...ctx, auth: anonymous }, makeContract('accepted'));

    assert.equal('authorization' in onlyCall().headers, false);
  });
});

describe('refused caravan requests show distinct messages', () => {
  it('asks the player to sign in on 401 and leaves the contract unchanged', async () => {
    upstream.reply(401, { detail: 'Not authenticated' });
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Sign in to continue with this caravan action.' });
    assert.equal(contract.status, 'accepted');
  });

  it('says not authorized on 403 for accept and leaves the contract open', async () => {
    upstream.reply(403, { detail: 'Forbidden' });
    const contract = makeContract('open');

    const result = await apiAcceptContract(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Your account is not authorized for this caravan action.' });
    assert.equal(contract.status, 'open');
  });

  it('says service unavailable on 503, with the server detail', async () => {
    upstream.reply(503, { detail: 'Caravan route service is unavailable.' });
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.deepEqual(result, { ok: false, message: 'Service unavailable: Caravan route service is unavailable.' });
    assert.equal(contract.status, 'accepted');
    assert.equal(contract.current_stage, 1);
  });

  it('shows the server detail for a 409', async () => {
    upstream.reply(409, { detail: 'Contract is already accepted.' });

    const result = await apiAcceptContract(ctx, makeContract('open'));

    assert.deepEqual(result, { ok: false, message: 'Contract is already accepted.' });
  });

  it('reports the status code when a 502 body has no detail', async () => {
    upstream.reply(502, '<html>bad gateway</html>');

    const result = await apiDispatchCaravan(ctx, makeContract('accepted'));

    assert.deepEqual(result, { ok: false, message: 'Request failed with status 502' });
  });

  it('reports a network error and leaves the contract in transit', async () => {
    const closed = createServer();
    await new Promise<void>((resolve) => closed.listen(0, '127.0.0.1', resolve));
    const deadBase = `http://127.0.0.1:${(closed.address() as AddressInfo).port}/api/v1`;
    await new Promise<void>((resolve) => closed.close(() => resolve()));
    const contract = makeContract('in_transit');

    const result = await apiFulfillContract({ ...ctx, apiBase: deadBase }, contract);

    assert.equal(result.ok, false);
    assert.match(result.ok ? '' : result.message, /^Network error: /);
    assert.equal(contract.status, 'in_transit');
  });
});

describe('successful caravan requests return a new contract and leave the input unchanged', () => {
  it('accept posts the contractor and takes the status from the reply', async () => {
    upstream.reply(200, { contract: { status: 'accepted', contractor_party_name: 'The Amber Vanguard' } });
    const contract = makeContract('open');

    const result = await apiAcceptContract(ctx, contract);

    assert.equal(result.ok, true);
    const call = onlyCall();
    assert.equal(call.path, '/api/v1/shared-worlds/world-1/caravans/contracts/contract-7/accept');
    assert.deepEqual(call.body, { contractor_campaign_id: 'camp-1', contractor_party_name: 'The Amber Vanguard' });
    const updated = result.ok ? result.data : contract;
    assert.notEqual(updated, contract);
    assert.equal(updated.status, 'accepted');
    assert.equal(updated.contractor_party_name, 'The Amber Vanguard');
    assert.equal(contract.status, 'open');
  });

  it('dispatch posts the campaign and marks the contract in transit', async () => {
    upstream.reply(200, {});
    const contract = makeContract('accepted');

    const result = await apiDispatchCaravan(ctx, contract);

    assert.equal(result.ok, true);
    const call = onlyCall();
    assert.equal(call.path, '/api/v1/shared-worlds/world-1/caravans/contracts/contract-7/dispatch');
    assert.deepEqual(call.body, { dispatched_by_campaign_id: 'camp-1' });
    const updated = result.ok ? result.data : contract;
    assert.notEqual(updated, contract);
    assert.equal(updated.status, 'in_transit');
    assert.equal(updated.current_stage, 1);
    assert.equal(contract.status, 'accepted');
  });

  it('fulfil posts to the fulfil route and marks the contract fulfilled', async () => {
    upstream.reply(200, {});
    const contract = makeContract('in_transit');

    const result = await apiFulfillContract(ctx, contract);

    assert.equal(result.ok, true);
    assert.equal(onlyCall().path, '/api/v1/shared-worlds/world-1/caravans/contracts/contract-7/fulfill');
    const updated = result.ok ? result.data : contract;
    assert.notEqual(updated, contract);
    assert.equal(updated.status, 'fulfilled');
    assert.equal(updated.current_stage, contract.transit_stages);
    assert.equal(contract.status, 'in_transit');
  });
});
