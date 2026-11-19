/**
 * App Shell data calls over the shared UI transport (TASK-0759).
 *
 * `requestData` and the overlay read `fetchPartyVitals` run over `request` from
 * `@runefoble/ui-core`. Only the network boundary (fetch) is replaced. The test checks the
 * request that leaves the shell and the DataResult that the views get.
 */

import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { fetchPartyVitals } from '../src/app/party-vitals-overlay.ts';
import { requestData } from '../src/services/shell-request.ts';
import { dataFailure, NETWORK_FAILURE_MESSAGE, UNREADABLE_RESPONSE_MESSAGE } from '../src/services/data-result.ts';

interface Sent { url: string; method: string; headers: Record<string, string> }

const realFetch = globalThis.fetch;
let sent: Sent[] = [];

function answer(reply: () => Response): void {
  sent = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    sent.push({ url: String(input), method: init?.method ?? 'GET', headers: { ...(init?.headers as Record<string, string>) } });
    return reply();
  }) as typeof fetch;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

describe('requestData', () => {
  it('sends no bearer when nobody is signed in and no caller identity header', async () => {
    answer(() => json(200, { ok: 1 }));

    const result = await requestData<{ ok: number }>('/api/v1/campaigns');

    assert.deepEqual(result, { ok: true, data: { ok: 1 } });
    assert.equal('Authorization' in sent[0].headers, false);
    assert.equal('x-user-id' in sent[0].headers, false);
  });

  it('sends a JSON body with the JSON content type', async () => {
    answer(() => json(201, { id: 'c1' }));

    await requestData('/api/v1/campaigns', { method: 'POST', body: JSON.stringify({ title: 'T' }) });

    assert.equal(sent[0].method, 'POST');
    assert.equal(sent[0].headers['Content-Type'], 'application/json');
  });

  it('keeps the status and the server detail of a refused call', async () => {
    answer(() => json(403, { detail: 'Not a campaign member.' }));

    assert.deepEqual(await requestData('/api/v1/campaigns/4'), dataFailure(403, 'Not a campaign member.'));
  });

  it('maps an unreadable 2xx body to the unreadable message with its status', async () => {
    answer(() => new Response('{not json', { status: 201 }));

    assert.deepEqual(await requestData('/api/v1/campaigns'), dataFailure(201, UNREADABLE_RESPONSE_MESSAGE));
  });

  it('maps a fetch TypeError to status 0 and the network message', async () => {
    answer(() => { throw new TypeError('fetch failed'); });

    assert.deepEqual(await requestData('/api/v1/campaigns'), dataFailure(0, NETWORK_FAILURE_MESSAGE));
  });
});

describe('fetchPartyVitals', () => {
  it('reads the overlay JSON route with the JSON Accept header', async () => {
    answer(() => json(200, { party: [], camera: null }));

    const result = await fetchPartyVitals('session 1', 'top');

    assert.equal(result.ok, true);
    assert.equal(sent[0].url, '/overlay/party-vitals/session%201?format=json&position=top');
    assert.equal(sent[0].headers.Accept, 'application/json');
  });

  it('shows the server detail of a refused read', async () => {
    answer(() => json(403, { detail: 'You may not observe this session.' }));

    assert.deepEqual(await fetchPartyVitals('s1', 'bottom'), dataFailure(403, 'You may not observe this session.'));
  });
});
