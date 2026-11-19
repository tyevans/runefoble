/**
 * No-battlemap-yet empty state (TASK-0906) and the DM set-up control (TASK-0922).
 * `<runefoble-board-empty>` runs in headless Chromium. The set-up flow posts to a live loopback
 * upstream through `apiBaseUrl`, with the shell bearer from `<runefoble-story-auth-provider>`.
 * Nothing replaces `fetch`. The test reads the upstream log, the rendered text and the
 * dispatched event, as a user and the host would.
 * Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-board-empty.ts';
import type { BoardSetUpDetail, RunefobleBoardEmpty } from '../src/runefoble-board-empty.ts';

interface Received { method: string; path: string; authorization: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const SEATS = [
  { characterId: 'char-valeros', characterName: 'Valeros the Bold' },
  { characterId: 'char-sarah', characterName: 'Sarah of the Mists' },
];

async function mount(canSetUpMap: boolean): Promise<RunefobleBoardEmpty> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = 'dm-token';
  const el = document.createElement('runefoble-board-empty');
  el.canSetUpMap = canSetUpMap;
  el.campaignId = 'camp-1';
  el.sessionId = 'sess-1';
  el.seats = SEATS;
  el.apiBaseUrl = await upstream.upstreamUrl();
  provider.append(el);
  document.body.append(provider);
  await el.updateComplete;
  return el;
}

function setUpButton(el: RunefobleBoardEmpty): HTMLButtonElement | null {
  return el.shadowRoot?.querySelector<HTMLButtonElement>('button.set-up') ?? null;
}

function nextSetUp(el: RunefobleBoardEmpty): Promise<BoardSetUpDetail> {
  return new Promise((resolve) => el.addEventListener('board-set-up', (e) => resolve((e as CustomEvent<BoardSetUpDetail>).detail), { once: true }));
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove()));

describe('runefoble-board-empty', () => {
  it('tells a player that the session has no battlemap yet, without a DM hint or control', async () => {
    const el = await mount(false);
    const status = el.shadowRoot?.querySelector('[role="status"]');
    expect(status?.textContent).toContain('No battlemap yet');
    expect(el.shadowRoot?.querySelector('[data-testid="board-empty-dm-hint"]')).toBeNull();
    expect(setUpButton(el)).toBeNull();
  });

  it('shows the DM a hint and the set-up control', async () => {
    const el = await mount(true);
    const hint = el.shadowRoot?.querySelector('[data-testid="board-empty-dm-hint"]');
    expect(hint?.textContent).toContain('Set up a battlemap');
    expect(setUpButton(el)?.textContent?.trim()).toBe('Set up battlemap');
  });

  it('creates the default board, then places one token for each seat at free start cells', async () => {
    await upstream.upstreamReply(200, { cols: 10, rows: 10 });
    const el = await mount(true);
    const done = nextSetUp(el);

    setUpButton(el)?.click();

    expect(await done).toEqual({ sessionId: 'sess-1', failure: null });
    const sent = await upstream.upstreamRequests();
    expect(sent.map((r) => `${r.method} ${r.path}`)).toEqual([
      'POST /api/v1/boards',
      'POST /api/v1/boards/sess-1/tokens',
      'POST /api/v1/boards/sess-1/tokens',
    ]);
    expect(sent.every((r) => r.authorization === 'Bearer dm-token')).toBe(true);
    expect(JSON.parse(sent[0].body)).toEqual({ campaign_id: 'camp-1', session_id: 'sess-1', cols: 10, rows: 10 });
    expect(sent.slice(1).map((r) => JSON.parse(r.body))).toEqual([
      { name: 'Valeros the Bold', token_type: 'pc', x: 0, y: 0, character_id: 'char-valeros' },
      { name: 'Sarah of the Mists', token_type: 'pc', x: 1, y: 0, character_id: 'char-sarah' },
    ]);
  });

  it('shows the owner error when the board is not created, and places no token', async () => {
    await upstream.upstreamReply(403, { detail: 'Forbidden: run_session on the campaign is required to create a board' });
    const el = await mount(true);
    let dispatched = false;
    el.addEventListener('board-set-up', () => { dispatched = true; });

    setUpButton(el)?.click();

    await expect.poll(() => el.shadowRoot?.querySelector('[role="alert"]')?.textContent ?? '').toContain('Forbidden: run_session');
    expect((await upstream.upstreamRequests()).map((r) => r.path)).toEqual(['/api/v1/boards']);
    expect(dispatched).toBe(false);
    expect(setUpButton(el)?.disabled).toBe(false);
  });
});
