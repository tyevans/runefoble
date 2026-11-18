/**
 * AssetImageController element tests (TASK-0797). A real Lit element hosts the controller and
 * renders `<img>` in a real Chromium DOM. Only the network is faked: `fetch` answers asset
 * reads, so the test sees what a user sees (the image source and the refusal message).
 * Blob URLs are real, so a revoked blob URL must fail to load in the browser.
 *
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { LitElement, html, type PropertyValues } from 'lit';
import { AssetImageController } from '../src/index.ts';

const ASSET_A = '/api/v1/assets/asset-a?stream=true';
const ASSET_B = '/api/v1/assets/asset-b?stream=true';
const TOKEN = 'tok-1';

/** The browser fetch, captured before any test stubs the global. Reads blob URLs. */
const browserFetch = window.fetch.bind(window);

class AssetImageFixture extends LitElement {
  static properties = { src: { type: String } };
  declare src: string;

  private readonly image = new AssetImageController(this, async () => ({
    Authorization: `Bearer ${TOKEN}`,
  }));

  override willUpdate(changed: PropertyValues) {
    super.willUpdate(changed);
    this.image.setSource(this.src ?? '');
  }

  override render() {
    const failure = this.image.failure;
    return html`${failure ? html`<p role="alert">${failure}</p>` : ''}<img alt="asset" src=${this.image.url} />`;
  }
}

const TAG = 'runefoble-test-asset-image';
if (!customElements.get(TAG)) customElements.define(TAG, AssetImageFixture);

/** Fake the network. Answers each asset path with its own bytes when the bearer matches. */
function stubAssetServer(status = 200) {
  const requests: Array<{ url: string; authorization: string | undefined }> = [];
  const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
    const headers = init?.headers as Record<string, string> | undefined;
    requests.push({ url: input, authorization: headers?.Authorization });
    if (status !== 200) return new Response('{"detail":"Not authenticated"}', { status });
    return new Response(`bytes-of ${input}`, { status: 200, headers: { 'Content-Type': 'image/png' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock, requests };
}

async function mount(src: string): Promise<AssetImageFixture> {
  const el = document.createElement(TAG) as AssetImageFixture;
  el.src = src;
  document.body.append(el);
  await el.updateComplete;
  return el;
}

function imageOf(el: AssetImageFixture): HTMLImageElement {
  const img = el.shadowRoot?.querySelector('img');
  if (!img) throw new Error('the element has no image');
  return img;
}

afterEach(() => {
  document.querySelectorAll(TAG).forEach((el) => el.remove());
  vi.unstubAllGlobals();
});

describe('AssetImageController in a Lit element', () => {
  it('shows an authorized asset as a blob URL that serves the fetched bytes', async () => {
    const { requests } = stubAssetServer();
    const el = await mount(ASSET_A);

    await vi.waitFor(() => expect(imageOf(el).getAttribute('src')).toMatch(/^blob:/));
    expect(requests).toEqual([{ url: ASSET_A, authorization: `Bearer ${TOKEN}` }]);
    const shown = await browserFetch(imageOf(el).getAttribute('src') ?? '');
    expect(await shown.text()).toBe(`bytes-of ${ASSET_A}`);
  });

  it('revokes the previous blob when the element shows a new asset', async () => {
    stubAssetServer();
    const el = await mount(ASSET_A);
    await vi.waitFor(() => expect(imageOf(el).getAttribute('src')).toMatch(/^blob:/));
    const first = imageOf(el).getAttribute('src') ?? '';

    el.src = ASSET_B;
    await el.updateComplete;
    await vi.waitFor(() => expect(imageOf(el).getAttribute('src')).not.toBe(first));

    await expect(browserFetch(first)).rejects.toThrow();
    const second = await browserFetch(imageOf(el).getAttribute('src') ?? '');
    expect(await second.text()).toBe(`bytes-of ${ASSET_B}`);
  });

  it('revokes the blob when the element leaves the document', async () => {
    stubAssetServer();
    const el = await mount(ASSET_A);
    await vi.waitFor(() => expect(imageOf(el).getAttribute('src')).toMatch(/^blob:/));
    const url = imageOf(el).getAttribute('src') ?? '';

    el.remove();

    await expect(browserFetch(url)).rejects.toThrow();
  });

  it('shows the refusal and no substitute image when the read is refused', async () => {
    stubAssetServer(401);
    const el = await mount(ASSET_A);

    await vi.waitFor(() => expect(el.shadowRoot?.querySelector('[role="alert"]')?.textContent).toMatch(/status 401/));
    expect(imageOf(el).getAttribute('src')).toBe('');
  });

  it('passes a plain or inline URL through without any request', async () => {
    const { fetchMock } = stubAssetServer();
    const inline = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg"/>';
    const el = await mount(inline);

    expect(imageOf(el).getAttribute('src')).toBe(inline);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
