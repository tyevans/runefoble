/**
 * Asset forge element over the shared transport (TASK-0758).
 * The element runs in headless Chromium. It calls a live loopback upstream through its
 * `apiBaseUrl`. The shell bearer comes from `<runefoble-story-auth-provider>`. Nothing
 * replaces `fetch`. The test reads the upstream log and the rendered alert, as a user would.
 * Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-asset-forge.ts';
import '../src/runefoble-print-forge.ts';

interface Received { method: string; path: string; authorization: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const TOKEN = 'dom-token';
const CAMPAIGN = '6f1d7c2e-0000-4000-8000-000000000001';

async function mount(tag: 'runefoble-asset-forge' | 'runefoble-print-forge'): Promise<HTMLElement> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = TOKEN;
  const el = document.createElement(tag) as HTMLElement & { apiBaseUrl: string; campaignId: string };
  el.apiBaseUrl = await upstream.upstreamUrl();
  el.campaignId = CAMPAIGN;
  provider.append(el);
  document.body.append(provider);
  await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;
  return el;
}

function clickButton(el: HTMLElement, label: string): void {
  const button = [...(el.shadowRoot?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.includes(label));
  if (!button) throw new Error(`No button "${label}"`);
  button.click();
}

async function alertText(el: HTMLElement): Promise<string> {
  await expect.poll(() => el.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim() ?? '').not.toBe('');
  return el.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim() ?? '';
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => {
  document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove());
});

describe('runefoble-asset-forge transport', () => {
  it('sends the battlemap request to the API base with the shell bearer', async () => {
    await upstream.upstreamReply(503, { detail: 'Silo asset storage is unavailable. The asset was not stored.' });
    const el = await mount('runefoble-asset-forge');

    clickButton(el, 'Forge Tactical Battlemap');
    await alertText(el);

    const [request] = await upstream.upstreamRequests();
    expect(request.method).toBe('POST');
    expect(request.path).toBe('/api/v1/forge/battlemap');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
    expect(JSON.parse(request.body).campaign_id).toBe(CAMPAIGN);
  });

  it('shows the server detail of a 503', async () => {
    await upstream.upstreamReply(503, { detail: 'Silo asset storage is unavailable. The asset was not stored.' });
    const el = await mount('runefoble-asset-forge');

    clickButton(el, 'Forge Tactical Battlemap');

    expect(await alertText(el)).toBe('Silo asset storage is unavailable. The asset was not stored.');
    expect(el.shadowRoot?.querySelector('img[alt="Forged Battlemap Preview"]')).toBeNull();
  });

  it('shows the permission message for a 403', async () => {
    await upstream.upstreamReply(403, { detail: "Forbidden: User 'u1' cannot forge assets for campaign 'c1'." });
    const el = await mount('runefoble-asset-forge');

    clickButton(el, 'Forge Tactical Battlemap');

    expect(await alertText(el)).toBe('Your account does not have permission for this forge action.');
  });
});

describe('runefoble-print-forge transport', () => {
  it('shows the server detail of a 503 for the PDF export', async () => {
    await upstream.upstreamReply(503, { detail: 'Silo asset storage is unavailable. The asset was not stored.' });
    const el = await mount('runefoble-print-forge');

    clickButton(el, 'Export Grid-Calibrated Multi-Page PDF');

    expect(await alertText(el)).toBe('Silo asset storage is unavailable. The asset was not stored.');
    const [request] = await upstream.upstreamRequests();
    expect(request.path).toBe('/api/v1/forge/print-pdf');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
  });

  it('shows the permission message for a 403', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden' });
    const el = await mount('runefoble-print-forge');

    clickButton(el, 'Export Grid-Calibrated Multi-Page PDF');

    expect(await alertText(el)).toBe('Your account does not have permission for this forge action.');
  });
});
