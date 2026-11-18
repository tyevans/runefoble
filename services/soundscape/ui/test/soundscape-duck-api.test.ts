import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { FetchLike } from '@runefoble/ui-core';
import { postDuck } from '../src/soundscape-duck-api.ts';

const request = { sessionId: 'session-tomb-14', isDucked: true, reason: 'thunder', durationMs: 2000 };

function recordingFetch(response: () => Response | Promise<Response>) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchImpl: FetchLike = async (url, init) => {
    calls.push({ url, init });
    return response();
  };
  return { calls, fetchImpl };
}

test('posts the duck to the gateway route with the owner body fields', async () => {
  const { calls, fetchImpl } = recordingFetch(() => new Response('{}', { status: 200 }));

  const result = await postDuck({ apiBase: 'https://gw.example', authorization: 'Bearer t' }, request, fetchImpl);

  assert.deepEqual(result, { ok: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://gw.example/api/v1/soundscape/duck');
  assert.equal(calls[0].init.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), {
    session_id: 'session-tomb-14',
    is_ducked: true,
    reason: 'thunder',
    duration_ms: 2000,
  });
  assert.equal((calls[0].init.headers as Record<string, string>)['Authorization'], 'Bearer t');
});

test('sends no Authorization header when none is configured', async () => {
  const { calls, fetchImpl } = recordingFetch(() => new Response('{}', { status: 200 }));

  await postDuck({ apiBase: '', authorization: '' }, request, fetchImpl);

  assert.equal(calls[0].url, '/api/v1/soundscape/duck');
  assert.equal('Authorization' in (calls[0].init.headers as Record<string, string>), false);
});

test('reports the owner detail when the gateway rejects the duck', async () => {
  const { fetchImpl } = recordingFetch(
    () => new Response(JSON.stringify({ detail: 'Forbidden: caller lacks Zanzibar permissions' }), { status: 403 })
  );

  const result = await postDuck({ apiBase: '', authorization: '' }, request, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Forbidden: caller lacks Zanzibar permissions' });
});

test('reports the HTTP status when a rejected reply has no JSON detail', async () => {
  const { fetchImpl } = recordingFetch(() => new Response('upstream down', { status: 503 }));

  const result = await postDuck({ apiBase: '', authorization: '' }, request, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Request failed with status 503' });
});

test('reports a network failure instead of throwing', async () => {
  const { fetchImpl } = recordingFetch(() => {
    throw new TypeError('fetch failed');
  });

  const result = await postDuck({ apiBase: '', authorization: '' }, request, fetchImpl);

  assert.deepEqual(result, { ok: false, message: 'Network error: fetch failed' });
});
