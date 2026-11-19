/**
 * Battlemap upload over the shared transport (TASK-0758).
 * `<runefoble-map-uploader>` runs in headless Chromium and posts a multipart upload to a
 * live loopback upstream through its `apiBaseUrl`. The shell bearer comes from
 * `<runefoble-story-auth-provider>`. Nothing replaces `fetch`. The test reads the upstream
 * log and the rendered error, as a user would.
 * Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-map-uploader.ts';

interface Received { method: string; path: string; authorization: string | null; contentType: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const TOKEN = 'dom-token';

async function mountUploader(): Promise<HTMLElement> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = TOKEN;
  const el = document.createElement('runefoble-map-uploader') as HTMLElement & { apiBaseUrl: string };
  el.apiBaseUrl = await upstream.upstreamUrl();
  provider.append(el);
  document.body.append(provider);
  await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;
  return el;
}

async function chooseMap(el: HTMLElement): Promise<void> {
  const dropzone = el.shadowRoot?.querySelector('runefoble-map-dropzone') as (HTMLElement & { updateComplete: Promise<boolean> }) | null;
  if (!dropzone) throw new Error('No dropzone');
  await dropzone.updateComplete;
  const input = dropzone.shadowRoot?.querySelector<HTMLInputElement>('#file-input');
  if (!input) throw new Error('No file input');
  const files = new DataTransfer();
  files.items.add(new File(['png-bytes'], 'crypt.png', { type: 'image/png' }));
  input.files = files.files;
  input.dispatchEvent(new Event('change'));
}

async function errorText(el: HTMLElement): Promise<string> {
  await expect.poll(() => el.shadowRoot?.querySelector('.status-msg.error')?.textContent?.trim() ?? '').not.toBe('');
  return el.shadowRoot?.querySelector('.status-msg.error')?.textContent?.trim() ?? '';
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => {
  document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove());
});

describe('runefoble-map-uploader transport', () => {
  it('posts the map as multipart to the API base with the shell bearer', async () => {
    await upstream.upstreamReply(503, { detail: 'Silo asset storage is unavailable.' });
    const el = await mountUploader();

    await chooseMap(el);
    await errorText(el);

    const [request] = await upstream.upstreamRequests();
    expect(request.method).toBe('POST');
    expect(request.path).toBe('/api/v1/assets/upload');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
    expect(request.contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect(request.body).toContain('filename="crypt.png"');
  });

  it('shows the server detail of a 503', async () => {
    await upstream.upstreamReply(503, { detail: 'Silo asset storage is unavailable.' });
    const el = await mountUploader();

    await chooseMap(el);

    expect(await errorText(el)).toContain('Upload failed: Silo asset storage is unavailable.');
  });

  it('shows the server detail of a 403', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden: you cannot upload assets to this campaign.' });
    const el = await mountUploader();

    await chooseMap(el);

    expect(await errorText(el)).toContain('Upload failed: Forbidden: you cannot upload assets to this campaign.');
  });
});
