/**
 * Encounter builder over the shared transport (TASK-0759).
 * `<runefoble-encounter-builder>` runs in headless Chromium. It posts the balance request to
 * a live loopback upstream through its `apiBaseUrl`. The shell bearer comes from
 * `<runefoble-story-auth-provider>`. Nothing replaces `fetch`. The test reads the upstream
 * log and the rendered roster or alert, as a DM would. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-encounter-builder.ts';

interface Received { method: string; path: string; authorization: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const TOKEN = 'encounter-dom-token';
const CAMPAIGN = '6f1d7c2e-0000-4000-8000-000000000002';
type Builder = HTMLElement & { updateComplete: Promise<boolean>; apiBaseUrl: string; campaignId: string | null };

async function mount(apiBaseUrl?: string): Promise<Builder> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = TOKEN;
  const el = document.createElement('runefoble-encounter-builder') as Builder;
  el.apiBaseUrl = apiBaseUrl ?? (await upstream.upstreamUrl());
  el.campaignId = CAMPAIGN;
  provider.append(el);
  document.body.append(provider);
  await el.updateComplete;
  return el;
}

function clickBalance(el: Builder): void {
  const button = [...(el.shadowRoot?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.includes('Auto-Balance'));
  if (!button) throw new Error('No Auto-Balance button');
  button.click();
}

async function alertText(el: Builder): Promise<string> {
  const read = () => el.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim() ?? '';
  await expect.poll(read).not.toBe('');
  return read();
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => {
  document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove());
});

describe('runefoble-encounter-builder transport', () => {
  it('posts the balance request with the shell bearer and drafts the reply', async () => {
    await upstream.upstreamReply(200, {
      target_difficulty: 'Medium',
      monsters: [{ name: 'Bugbear', cr: 1, xp: 200, role: 'brute', count: 2 }],
      tactical_summary: 'The bugbears ambush from the ridge.',
    });
    const el = await mount();

    clickBalance(el);

    await expect.poll(() => el.shadowRoot?.textContent ?? '').toContain('The bugbears ambush from the ridge.');
    expect(el.shadowRoot?.textContent).toContain('Bugbear');
    const [request] = await upstream.upstreamRequests();
    expect(request.method).toBe('POST');
    expect(request.path).toBe('/api/v1/compendium/encounters/balance');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
    expect(JSON.parse(request.body)).toEqual({ party_levels: [3, 3, 3, 3], target_difficulty: 'Medium', campaign_id: CAMPAIGN });
  });

  it('shows the not-authorized text on a 403', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden' });
    const el = await mount();

    clickBalance(el);

    expect(await alertText(el)).toBe('Your account is not authorized for this encounter balance request.');
  });

  it('shows the service-unavailable text on a 503', async () => {
    await upstream.upstreamReply(503, { detail: 'The rules index is unavailable.' });
    const el = await mount();

    clickBalance(el);

    expect(await alertText(el)).toBe('Service unavailable: The rules index is unavailable.');
  });

  it('shows the server detail on a 422', async () => {
    await upstream.upstreamReply(422, { detail: [{ msg: 'party_levels must not be empty' }] });
    const el = await mount();

    clickBalance(el);

    expect(await alertText(el)).toBe('party_levels must not be empty');
  });

  it('reports a missing service address and sends nothing', async () => {
    const el = await mount('');

    clickBalance(el);

    expect(await alertText(el)).toBe('The compendium service address is not set.');
    expect(await upstream.upstreamRequests()).toEqual([]);
  });
});
