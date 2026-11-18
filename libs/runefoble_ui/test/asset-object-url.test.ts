import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { fetchAssetObjectUrl, revokeAssetObjectUrl } from '../src/index.ts';

const ASSET_URL = 'http://runefoble.test/api/v1/assets/asset-1?stream=true';

/** A server stand-in: answers 200 with the bytes only when the bearer matches. */
function guardedFetch(token: string) {
  const seen: Array<{ url: string; headers: Record<string, string> }> = [];
  const fetchImpl = async (input: string, init?: RequestInit) => {
    const headers = { ...(init?.headers as Record<string, string> | undefined) };
    seen.push({ url: input, headers });
    if (headers.Authorization === `Bearer ${token}`) {
      return new Response('<svg/>', { status: 200, headers: { 'Content-Type': 'image/svg+xml' } });
    }
    return new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 });
  };
  return { fetchImpl, seen };
}

const realCreateObjectUrl = URL.createObjectURL;
afterEach(() => {
  URL.createObjectURL = realCreateObjectUrl;
});

describe('fetchAssetObjectUrl', () => {
  it('sends the bearer and returns a blob URL that holds the fetched bytes', async () => {
    const { fetchImpl, seen } = guardedFetch('tok-1');
    const blobs: Blob[] = [];
    URL.createObjectURL = (blob: Blob | MediaSource) => {
      blobs.push(blob as Blob);
      return 'blob:runefoble-test-1';
    };

    const objectUrl = await fetchAssetObjectUrl(
      ASSET_URL,
      async () => ({ Authorization: 'Bearer tok-1' }),
      fetchImpl,
    );

    assert.equal(objectUrl, 'blob:runefoble-test-1');
    assert.equal(seen[0].url, ASSET_URL);
    assert.equal(seen[0].headers.Authorization, 'Bearer tok-1');
    assert.equal(blobs.length, 1);
    assert.equal(blobs[0].type, 'image/svg+xml');
    assert.equal(await blobs[0].text(), '<svg/>');
  });

  it('rejects with the status and makes no blob when the server refuses', async () => {
    const { fetchImpl } = guardedFetch('tok-1');
    let created = false;
    URL.createObjectURL = () => {
      created = true;
      return 'blob:should-not-exist';
    };

    await assert.rejects(
      fetchAssetObjectUrl(ASSET_URL, async () => ({}), fetchImpl),
      /status 401/,
    );
    assert.equal(created, false);
  });
});

describe('revokeAssetObjectUrl', () => {
  it('ignores URLs that are not blob URLs', () => {
    assert.doesNotThrow(() => revokeAssetObjectUrl('/api/v1/assets/asset-1?stream=true'));
    assert.doesNotThrow(() => revokeAssetObjectUrl(null));
    assert.doesNotThrow(() => revokeAssetObjectUrl(undefined));
  });
});
