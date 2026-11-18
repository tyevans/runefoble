import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import type { ReactiveControllerHost } from 'lit';
import { AssetImageController, isAuthorizedAssetPath } from '../src/index.ts';

const ASSET_A = '/api/v1/assets/asset-a?stream=true';
const ASSET_B = '/api/v1/assets/asset-b?stream=true';
const TOKEN = 'tok-1';

/** A host stand-in that records controllers and update requests. */
function fakeHost() {
  const controllers: unknown[] = [];
  let updates = 0;
  const host = {
    addController(c: unknown) {
      controllers.push(c);
    },
    removeController() {},
    requestUpdate() {
      updates += 1;
    },
    updateComplete: Promise.resolve(true),
  };
  return { host: host as unknown as ReactiveControllerHost, controllers, updates: () => updates };
}

/** Answers each asset path with its own bytes. Records every request. */
function serverFetch() {
  const requested: string[] = [];
  const fetchImpl = async (input: string, init?: RequestInit) => {
    requested.push(input);
    const auth = (init?.headers as Record<string, string> | undefined)?.Authorization;
    if (auth !== `Bearer ${TOKEN}`) {
      return new Response('{"detail":"Not authenticated"}', { status: 401 });
    }
    return new Response(`bytes-of ${input}`, { status: 200, headers: { 'Content-Type': 'image/png' } });
  };
  return { fetchImpl, requested };
}

const realCreate = URL.createObjectURL;
const realRevoke = URL.revokeObjectURL;
let blobCount = 0;
let revoked: string[] = [];

beforeEach(() => {
  blobCount = 0;
  revoked = [];
  URL.createObjectURL = () => {
    blobCount += 1;
    return `blob:runefoble-test-${blobCount}`;
  };
  URL.revokeObjectURL = (url: string) => {
    revoked.push(url);
  };
});

afterEach(() => {
  URL.createObjectURL = realCreate;
  URL.revokeObjectURL = realRevoke;
});

const bearer = async () => ({ Authorization: `Bearer ${TOKEN}` });

/** Waits for pending promise callbacks to settle. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('isAuthorizedAssetPath', () => {
  it('matches only the authorized asset route', () => {
    assert.equal(isAuthorizedAssetPath(ASSET_A), true);
    assert.equal(isAuthorizedAssetPath('/assets/portraits/default.svg'), false);
    assert.equal(isAuthorizedAssetPath('data:image/png;base64,AAAA'), false);
  });
});

describe('AssetImageController', () => {
  it('passes a non-asset source through without a request', async () => {
    const { host, controllers } = fakeHost();
    const { fetchImpl, requested } = serverFetch();
    const image = new AssetImageController(host, bearer, fetchImpl);
    assert.equal(controllers.length, 1);

    image.hostConnected();
    image.setSource('/assets/portraits/default.svg');
    await settle();

    assert.equal(image.url, '/assets/portraits/default.svg');
    assert.deepEqual(requested, []);
  });

  it('loads an asset path with the bearer and shows the blob URL', async () => {
    const { host } = fakeHost();
    const { fetchImpl, requested } = serverFetch();
    const image = new AssetImageController(host, bearer, fetchImpl);

    image.hostConnected();
    image.setSource(ASSET_A);
    await settle();

    assert.deepEqual(requested, [ASSET_A]);
    assert.equal(image.url, 'blob:runefoble-test-1');
    assert.equal(image.failure, '');
  });

  it('revokes the previous blob when the source changes', async () => {
    const { host } = fakeHost();
    const { fetchImpl } = serverFetch();
    const image = new AssetImageController(host, bearer, fetchImpl);

    image.hostConnected();
    image.setSource(ASSET_A);
    await settle();
    image.setSource(ASSET_B);
    await settle();

    assert.equal(image.url, 'blob:runefoble-test-2');
    assert.ok(revoked.includes('blob:runefoble-test-1'), 'the first blob must be revoked');
    assert.ok(!revoked.includes('blob:runefoble-test-2'));
  });

  it('revokes the blob and requests nothing while the host is disconnected', async () => {
    const { host } = fakeHost();
    const { fetchImpl, requested } = serverFetch();
    const image = new AssetImageController(host, bearer, fetchImpl);

    image.hostConnected();
    image.setSource(ASSET_A);
    await settle();
    image.hostDisconnected();

    assert.equal(image.url, '');
    assert.ok(revoked.includes('blob:runefoble-test-1'));

    image.setSource(ASSET_B);
    await settle();
    assert.deepEqual(requested, [ASSET_A], 'no request while disconnected');
  });

  it('reloads the current asset when the host connects again', async () => {
    const { host } = fakeHost();
    const { fetchImpl, requested } = serverFetch();
    const image = new AssetImageController(host, bearer, fetchImpl);

    image.setSource(ASSET_A);
    image.hostConnected();
    await settle();
    image.hostDisconnected();
    image.hostConnected();
    await settle();

    assert.deepEqual(requested, [ASSET_A, ASSET_A]);
    assert.equal(image.url, 'blob:runefoble-test-2');
  });

  it('records a refused read and shows no substitute image', async () => {
    const { host, updates } = fakeHost();
    const { fetchImpl } = serverFetch();
    const badBearer = async () => ({ Authorization: 'Bearer wrong' });
    const image = new AssetImageController(host, badBearer, fetchImpl);

    image.hostConnected();
    image.setSource(ASSET_A);
    await settle();

    assert.equal(image.url, '');
    assert.match(image.failure, /status 401/);
    assert.ok(updates() > 0, 'the host is asked to render the failure');
  });

  it('discards a slow load that a newer source has replaced', async () => {
    const { host } = fakeHost();
    const releases: Array<() => void> = [];
    const slowFetch = (input: string) =>
      new Promise<Response>((resolve) => {
        releases.push(() => resolve(new Response(`bytes-of ${input}`, { status: 200 })));
      });
    const image = new AssetImageController(host, bearer, slowFetch);

    image.hostConnected();
    image.setSource(ASSET_A);
    image.setSource(ASSET_B);
    await settle();
    assert.equal(releases.length, 2, 'both requests are in flight');
    // Answer the newer request first, then the older one.
    releases[1]();
    await settle();
    assert.equal(image.url, 'blob:runefoble-test-1');
    releases[0]();
    await settle();

    assert.equal(image.url, 'blob:runefoble-test-1', 'the stale load must not replace the newer one');
    assert.ok(revoked.includes('blob:runefoble-test-2'), 'the stale blob must be revoked');
  });
});
