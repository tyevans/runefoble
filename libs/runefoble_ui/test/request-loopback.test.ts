/**
 * Tests for the shared transport `request` (TASK-0758).
 * The requests go to a real HTTP server on the loopback interface. Nothing replaces `fetch`.
 * The server (`testing/loopback-upstream.ts`) records each request and answers with the reply each test sets.
 */

import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import type { AddressInfo } from 'node:net';
import {
  HttpError, actionFailureMessage, postForm, postJson, request, requestFailureMessage, UnreadableResponseError,
  type AuthSource,
} from '../src/index.ts';
import { startLoopbackUpstream, type LoopbackUpstream } from '../testing/loopback-upstream.ts';

let upstream: LoopbackUpstream;
let base = '';

before(async () => {
  upstream = await startLoopbackUpstream();
  base = upstream.url;
});

after(() => upstream.close());

beforeEach(() => upstream.reset());

function received(index: number) {
  const req = upstream.requests[index];
  return {
    method: req.method,
    path: req.path,
    authorization: req.headers.authorization,
    contentType: req.headers['content-type'],
    body: req.body,
  };
}

const signedIn: AuthSource = { authHeaders: async () => ({ Authorization: 'Bearer loopback-token' }) };
const anonymous: AuthSource = { authHeaders: async () => ({}) };

describe('request over a live loopback server', () => {
  it('sends the path under the API base with the bearer from the auth source', async () => {
    upstream.reply(200, { id: 'b1' });

    const result = await request<{ id: string }>('/api/v1/boards/b1', {}, { apiBase: `${base}/`, auth: signedIn });

    assert.deepEqual(result, { id: 'b1' });
    assert.equal(received(0).method, 'GET');
    assert.equal(received(0).path, '/api/v1/boards/b1');
    assert.equal(received(0).authorization, 'Bearer loopback-token');
  });

  it('sends no Authorization header when the auth source has no token', async () => {
    await request('/api/v1/x', {}, { apiBase: base, auth: anonymous });

    assert.equal(received(0).authorization, undefined);
  });

  it('posts JSON with the JSON content type', async () => {
    await postJson('/api/v1/forge/battlemap', { prompt: 'Crypt' }, { apiBase: base, auth: signedIn });

    assert.equal(received(0).method, 'POST');
    assert.equal(received(0).contentType, 'application/json');
    assert.deepEqual(JSON.parse(received(0).body), { prompt: 'Crypt' });
  });

  it('posts FormData as multipart with the boundary that fetch sets', async () => {
    upstream.reply(200, { asset_id: 'a1' });
    const form = new FormData();
    form.append('owner_id', 'gm-host');
    form.append('file', new Blob(['png-bytes'], { type: 'image/png' }), 'map.png');

    const result = await postForm<{ asset_id: string }>('/api/v1/assets/upload', form, { apiBase: base, auth: signedIn });

    assert.deepEqual(result, { asset_id: 'a1' });
    assert.match(received(0).contentType ?? '', /^multipart\/form-data; boundary=/);
    assert.equal(received(0).authorization, 'Bearer loopback-token');
    assert.match(received(0).body, /name="owner_id"\r\n\r\ngm-host/);
    assert.match(received(0).body, /filename="map.png"/);
  });

  it('throws HttpError with the FastAPI detail of a 403', async () => {
    upstream.reply(403, { detail: 'Forbidden: DM only' });

    await assert.rejects(request('/api/v1/x', {}, { apiBase: base, auth: signedIn }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.status, 403);
      assert.equal(err.detail, 'Forbidden: DM only');
      return true;
    });
  });

  it('throws HttpError with the status when a 503 body is not JSON', async () => {
    upstream.reply(503, 'upstream down');

    await assert.rejects(request('/api/v1/x', {}, { apiBase: base }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.status, 503);
      assert.equal(requestFailureMessage(err), 'Request failed with status 503');
      return true;
    });
  });

  it('reads the message of an engine-unavailable body that has no detail', async () => {
    upstream.reply(503, { error: 'map_generation_unavailable', generator: 'deterministic', message: 'The map generator is down.' });

    await assert.rejects(request('/api/v1/forge/battlemap', {}, { apiBase: base }), (err: unknown) => {
      assert.ok(err instanceof HttpError);
      assert.equal(err.detail, 'The map generator is down.');
      return true;
    });
  });

  it('throws UnreadableResponseError with the status when a 2xx body is not JSON (TASK-0759)', async () => {
    upstream.reply(200, '{not json');

    await assert.rejects(request('/api/v1/x', {}, { apiBase: base }), (err: unknown) => {
      assert.ok(err instanceof UnreadableResponseError);
      assert.equal(err.status, 200);
      assert.equal(requestFailureMessage(err), 'The server sent a response that could not be read.');
      return true;
    });
  });

  it('lets the extra headers win over the auth headers', async () => {
    await request('/api/v1/x', {}, { apiBase: base, auth: signedIn, headers: { Authorization: 'Bearer other' } });

    assert.equal(received(0).authorization, 'Bearer other');
  });

  it('rejects with the fetch error when nothing listens on the port', async () => {
    const closed = createServer();
    await new Promise<void>((resolve) => closed.listen(0, '127.0.0.1', resolve));
    const deadBase = `http://127.0.0.1:${(closed.address() as AddressInfo).port}`;
    await new Promise<void>((resolve) => closed.close(() => resolve()));

    await assert.rejects(request('/api/v1/x', {}, { apiBase: deadBase }), (err: unknown) => {
      assert.ok(err instanceof TypeError);
      assert.ok(!(err instanceof HttpError));
      return true;
    });
  });
});

describe('actionFailureMessage over a live loopback server (TASK-0759)', () => {
  async function messageFor(status: number, body: unknown): Promise<string> {
    upstream.reply(status, body);
    try {
      await request('/api/v1/x', {}, { apiBase: base, auth: signedIn });
    } catch (err) {
      return actionFailureMessage(err, 'caravan action');
    }
    throw new assert.AssertionError({ message: 'The call resolved. It must reject.' });
  }

  it('asks the user to sign in on a 401', async () => {
    assert.equal(await messageFor(401, { detail: 'Not authenticated' }), 'Sign in to continue with this caravan action.');
  });

  it('says not authorized on a 403, not the raw detail', async () => {
    assert.equal(await messageFor(403, { detail: 'Forbidden' }), 'Your account is not authorized for this caravan action.');
  });

  it('says service unavailable on a 503 and keeps the server detail', async () => {
    assert.equal(
      await messageFor(503, { detail: 'Caravan route service is unavailable.' }),
      'Service unavailable: Caravan route service is unavailable.',
    );
  });

  it('says service unavailable on a 503 that has no detail', async () => {
    assert.equal(await messageFor(503, 'upstream down'), 'Service unavailable. Try again later.');
  });

  it('shows the server detail for other codes', async () => {
    assert.equal(await messageFor(409, { detail: 'Contract is already accepted.' }), 'Contract is already accepted.');
  });

  it('gives distinct text for 403 and 503', async () => {
    assert.notEqual(await messageFor(403, { detail: 'x' }), await messageFor(503, { detail: 'x' }));
  });

  it('reports a network failure as a network error', () => {
    assert.equal(actionFailureMessage(new TypeError('Failed to fetch'), 'caravan action'), 'Network error: Failed to fetch');
  });
});
