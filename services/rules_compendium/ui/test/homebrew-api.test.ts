import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { FetchLike } from '@runefoble/ui-core';
import { postHomebrewRule } from '../src/homebrew-api.ts';
import type { HomebrewCreateRequest } from '../src/types.ts';

const payload: HomebrewCreateRequest = {
  campaign_id: 'campaign-homebrew-lab',
  rule_type: 'monster',
  title: 'Abyssal Stalker',
  content: { challenge_rating: 3, description: 'Lurks in the dark.' },
};

const authHeaders = async () => ({ Authorization: 'Bearer dm-token' });

function recordingFetch(response: () => Response | Promise<Response>) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchImpl: FetchLike = async (url, init) => {
    calls.push({ url, init: init ?? {} });
    return response();
  };
  return { calls, fetchImpl };
}

test('posts the rule to the gateway route with the bearer and no user header', async () => {
  const created = { rule_id: 'hb-1', campaign_id: 'campaign-homebrew-lab', author_id: 'dm', rule_type: 'monster', title: 'Abyssal Stalker', content: {}, status: 'registered' };
  const { calls, fetchImpl } = recordingFetch(() => new Response(JSON.stringify(created), { status: 200 }));

  const result = await postHomebrewRule({ apiBase: 'https://gw.example', authHeaders }, payload, fetchImpl);

  assert.deepEqual(result, { ok: true, rule: created });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://gw.example/api/v1/compendium/homebrew');
  assert.equal(calls[0].init.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), payload);
  const headers = calls[0].init.headers as Record<string, string>;
  assert.equal(headers['Authorization'], 'Bearer dm-token');
  assert.equal(headers['Content-Type'], 'application/json');
  assert.equal('x-user-id' in headers, false);
});

test('reports the server detail when the gateway rejects the rule', async () => {
  const { fetchImpl } = recordingFetch(
    () => new Response(JSON.stringify({ detail: 'Registration is unavailable.' }), { status: 503 })
  );

  const result = await postHomebrewRule({ apiBase: '', authHeaders }, payload, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Registration is unavailable.' });
});

test('reports the HTTP status when a rejected reply has no JSON detail', async () => {
  const { fetchImpl } = recordingFetch(() => new Response('upstream down', { status: 502 }));

  const result = await postHomebrewRule({ apiBase: '', authHeaders }, payload, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Request failed with status 502' });
});

test('reports a 2xx reply that carries no rule body as a failure', async () => {
  const { fetchImpl } = recordingFetch(() => new Response('', { status: 200 }));

  const result = await postHomebrewRule({ apiBase: '', authHeaders }, payload, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'The server did not return the registered rule.' });
});

test('reports a network failure instead of throwing', async () => {
  const { fetchImpl } = recordingFetch(() => {
    throw new TypeError('fetch failed');
  });

  const result = await postHomebrewRule({ apiBase: '', authHeaders }, payload, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Network error: fetch failed' });
});
