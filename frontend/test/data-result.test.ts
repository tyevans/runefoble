/**
 * DataResult Unit Tests (TASK-0640).
 *
 * Covers the result helpers and the request() mapping from HTTP responses to typed results.
 * The gateway is faked at the fetch boundary. Governing ADRs: ADR-0007, ADR-0014
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  dataOk, dataFailure, errorMessageFromBody, isNotFound, NETWORK_FAILURE_MESSAGE,
  UNREADABLE_RESPONSE_MESSAGE, type DataResult,
} from '../src/services/data-result.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { installFakeGateway, type FakeGateway } from './support/fake-gateway.ts';

describe('DataResult helpers', () => {
  it('dataOk wraps data with ok true and no status', () => {
    assert.deepEqual(dataOk([1, 2]), { ok: true, data: [1, 2] });
  });

  it('dataFailure carries the status and the message', () => {
    assert.deepEqual(dataFailure(409, 'Locked'), { ok: false, status: 409, message: 'Locked' });
  });

  it('isNotFound is true only for a 404 failure', () => {
    const notFound: DataResult<number> = dataFailure(404, 'missing');
    const serverError: DataResult<number> = dataFailure(500, 'boom');
    assert.equal(isNotFound(notFound), true);
    assert.equal(isNotFound(serverError), false);
    assert.equal(isNotFound(dataOk(1)), false);
  });
});

describe('errorMessageFromBody', () => {
  it('uses a string detail field', () => {
    assert.equal(errorMessageFromBody({ detail: 'Campaign title is required' }, 422), 'Campaign title is required');
  });

  it('joins FastAPI validation detail messages', () => {
    const body = { detail: [{ loc: ['body', 'title'], msg: 'field required' }, { loc: ['body', 'system'], msg: 'invalid system' }] };
    assert.equal(errorMessageFromBody(body, 422), 'field required; invalid system');
  });

  it('uses a message field when detail is absent', () => {
    assert.equal(errorMessageFromBody({ message: 'Rate limited' }, 429), 'Rate limited');
  });

  it('uses an error field when detail and message are absent', () => {
    assert.equal(errorMessageFromBody({ error: 'Forbidden here' }, 403), 'Forbidden here');
  });

  it('ignores blank detail strings and falls back to the status text', () => {
    assert.equal(errorMessageFromBody({ detail: '   ' }, 500), 'The request failed with status 500.');
  });

  it('gives a not-found sentence for a 404 with no readable body', () => {
    assert.equal(errorMessageFromBody(null, 404), 'The requested item was not found.');
  });

  it('gives a status sentence for a non-object body', () => {
    assert.equal(errorMessageFromBody('<html>', 502), 'The request failed with status 502.');
  });
});

describe('AppDataService.request maps HTTP responses to DataResult', () => {
  let gateway: FakeGateway | undefined;
  const service = new AppDataService();
  const realFetch = globalThis.fetch;

  afterEach(() => {
    gateway?.restore();
    gateway = undefined;
    globalThis.fetch = realFetch;
  });

  it('maps a 200 JSON body to ok with the parsed data', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/4': { body: { id: '4', title: 'Tomb' } } });
    assert.deepEqual(await service.request<any>('/campaigns/4'), { ok: true, data: { id: '4', title: 'Tomb' } });
  });

  it('maps an empty 204 body to ok with an empty object', async () => {
    gateway = installFakeGateway({ 'DELETE /api/v1/campaigns/4/members/u1': { status: 204 } });
    assert.deepEqual(await service.request<void>('/campaigns/4/members/u1', { method: 'DELETE' }), { ok: true, data: {} });
  });

  it('maps a 404 to a not-found failure with the server detail', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/campaigns/nope': { status: 404, body: { detail: 'Campaign not found' } } });
    const result = await service.request<any>('/campaigns/nope');
    assert.equal(result.ok, false);
    assert.equal(isNotFound(result), true);
    assert.equal(result.ok === false && result.message, 'Campaign not found');
  });

  it('maps a 500 with no JSON body to a failure with the status message', async () => {
    gateway = installFakeGateway({ 'GET /api/v1/characters': { status: 500 } });
    const result = await service.request<any>('/characters');
    assert.deepEqual(result, dataFailure(500, 'The request failed with status 500.'));
  });

  it('maps a network exception to status 0 with the network message', async () => {
    globalThis.fetch = (async () => { throw new TypeError('fetch failed'); }) as typeof fetch;
    const result = await service.request<any>('/campaigns');
    assert.deepEqual(result, dataFailure(0, NETWORK_FAILURE_MESSAGE));
  });

  it('maps an unreadable 200 body to a failure, not to empty data', async () => {
    globalThis.fetch = (async () => new Response('{not json', { status: 200 })) as typeof fetch;
    const result = await service.request<any>('/campaigns');
    assert.deepEqual(result, dataFailure(200, UNREADABLE_RESPONSE_MESSAGE));
  });

  it('maps an unreadable error body to the status message, not to a parse crash', async () => {
    globalThis.fetch = (async () => new Response('<html>Bad Gateway</html>', { status: 502 })) as typeof fetch;
    const result = await service.request<any>('/campaigns');
    assert.deepEqual(result, dataFailure(502, 'The request failed with status 502.'));
  });
});
