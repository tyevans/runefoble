/**
 * Tests for the shared HTTP and socket helpers (TASK-0825, audit F-05 and F-06).
 * Only the network boundary (fetch) is replaced. The helpers run unchanged.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  HttpError,
  bearerHeaders,
  postJson,
  requestFailureMessage,
  request,
  wsUrl,
} from '../src/index.ts';

interface Captured {
  url: string;
  init: RequestInit;
}

function recordingFetch(respond: () => Response | Promise<Response>) {
  const calls: Captured[] = [];
  const fetchImpl = async (url: string, init?: RequestInit) => {
    calls.push({ url, init: init ?? {} });
    return respond();
  };
  return { calls, fetchImpl };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('postJson', () => {
  it('posts a JSON body with the JSON content type and the given headers', async () => {
    const { calls, fetchImpl } = recordingFetch(() => jsonResponse(200, { id: 'a1' }));

    const result = await postJson<{ id: string }>('/api/v1/things', { name: 'x' }, {
      headers: { Authorization: 'Bearer t1' },
      fetchImpl,
    });

    assert.deepEqual(result, { id: 'a1' });
    assert.equal(calls[0].url, '/api/v1/things');
    assert.equal(calls[0].init.method, 'POST');
    assert.equal(calls[0].init.body, JSON.stringify({ name: 'x' }));
    assert.deepEqual(calls[0].init.headers, { 'Content-Type': 'application/json', Authorization: 'Bearer t1' });
  });

  it('keeps the parsed error body on HttpError, so a caller can read more fields than detail', async () => {
    const body = { detail: 'Ghost: Forbidden', token: 'Ghost', board_created: true };
    const { fetchImpl } = recordingFetch(() => jsonResponse(403, body));

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.deepEqual(err.body, body);
      return true;
    });
  });

  it('gives HttpError an undefined body when the error body is not JSON', async () => {
    const { fetchImpl } = recordingFetch(() => new Response('upstream down', { status: 502 }));

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.body, undefined);
      return true;
    });
  });

  it('throws HttpError carrying the server detail on a rejected request', async () => {
    const { fetchImpl } = recordingFetch(() => jsonResponse(403, { detail: 'Forbidden: DM only' }));

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.status, 403);
      assert.equal(err.detail, 'Forbidden: DM only');
      assert.equal(err.message, 'Forbidden: DM only');
      return true;
    });
  });

  it('joins FastAPI validation messages from a 422 body', async () => {
    const { fetchImpl } = recordingFetch(() =>
      jsonResponse(422, { detail: [{ msg: 'too short' }, { msg: 'too large' }] }),
    );

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.detail, 'too short; too large');
      return true;
    });
  });

  it('reports the status when the error body is not JSON', async () => {
    const { fetchImpl } = recordingFetch(() => new Response('upstream down', { status: 502 }));

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.status, 502);
      assert.equal(err.detail, 'Request failed with status 502');
      return true;
    });
  });

  it('resolves with undefined for an empty success body', async () => {
    const { fetchImpl } = recordingFetch(() => new Response(null, { status: 204 }));

    assert.equal(await postJson('/api/v1/x', {}, { fetchImpl }), undefined);
  });

  it('lets a network failure propagate as the fetch error', async () => {
    const { fetchImpl } = recordingFetch(() => {
      throw new TypeError('Failed to fetch');
    });

    await assert.rejects(postJson('/api/v1/x', {}, { fetchImpl }), (err: unknown) => {
      assert.ok(err instanceof TypeError);
      assert.equal(err.message, 'Failed to fetch');
      return true;
    });
  });
});

describe('request', () => {
  it('sends a GET with no body and no JSON content type', async () => {
    const { calls, fetchImpl } = recordingFetch(() => jsonResponse(200, { ok: 1 }));

    assert.deepEqual(await request<{ ok: number }>('/api/v1/y', {}, { fetchImpl }), { ok: 1 });
    assert.equal(calls[0].init.method, undefined);
    assert.deepEqual(calls[0].init.headers, {});
  });
});

describe('requestFailureMessage', () => {
  it('returns the server detail for an HttpError', () => {
    assert.equal(requestFailureMessage(new HttpError(503, 'Store is down')), 'Store is down');
  });

  it('names a network failure for any other error', () => {
    assert.equal(requestFailureMessage(new TypeError('Failed to fetch')), 'Network error: Failed to fetch');
  });
});

describe('bearerHeaders', () => {
  it('returns an Authorization header for a token', () => {
    assert.deepEqual(bearerHeaders('tok-1'), { Authorization: 'Bearer tok-1' });
  });

  it('returns no headers without a token', () => {
    assert.deepEqual(bearerHeaders(null), {});
    assert.deepEqual(bearerHeaders(''), {});
  });
});

describe('wsUrl', () => {
  it('uses wss on an https page and ws on an http page', () => {
    assert.equal(wsUrl('/ws/session/s1', { protocol: 'https:', host: 'app.example' }), 'wss://app.example/ws/session/s1');
    assert.equal(wsUrl('/ws/boards/b1', { protocol: 'http:', host: 'localhost:8000' }), 'ws://localhost:8000/ws/boards/b1');
  });
});
