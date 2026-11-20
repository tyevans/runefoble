/**
 * Dice roller over the shared transport (TASK-0951).
 * `<runefoble-dice-roller>` runs in headless Chromium. It posts each roll to a live loopback
 * upstream, and it shows the reply. The browser computes no roll for a session. Nothing replaces
 * `fetch`. Governing ADRs: ADR-0013, ADR-0014, ADR-0015.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';
import '@runefoble/ui-core/story-auth-provider';
import '../src/runefoble-dice-roller.ts';

interface Received { method: string; path: string; authorization: string | null; body: string }

const upstream = commands as unknown as {
  upstreamUrl(): Promise<string>;
  upstreamReply(status: number, body: unknown): Promise<void>;
  upstreamReset(): Promise<void>;
  upstreamRequests(): Promise<Received[]>;
};

const TOKEN = 'dice-dom-token';
type Roller = HTMLElement & { apiBaseUrl: string; rollerName: string; sessionId: string; updateComplete: Promise<boolean> };

async function mount(rollerName: string): Promise<Roller> {
  const provider = document.createElement('runefoble-story-auth-provider') as HTMLElement & { token: string };
  provider.token = TOKEN;
  const roller = document.createElement('runefoble-dice-roller') as Roller;
  roller.apiBaseUrl = await upstream.upstreamUrl();
  roller.sessionId = 'session-7';
  roller.rollerName = rollerName;
  provider.append(roller);
  document.body.append(provider);
  await roller.updateComplete;
  return roller;
}

function rollButton(roller: Roller): HTMLButtonElement | null {
  return roller.shadowRoot?.querySelector<HTMLButtonElement>('.roll-action-btn') ?? null;
}

function shownTotal(roller: Roller): string {
  return roller.shadowRoot?.querySelector('.score-total')?.textContent?.trim() ?? '';
}

function alertText(roller: Roller): string {
  return roller.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim() ?? '';
}

beforeEach(() => upstream.upstreamReset());

afterEach(() => {
  document.querySelectorAll('runefoble-story-auth-provider').forEach((el) => el.remove());
});

describe('runefoble-dice-roller transport', () => {
  it('posts the formula and the character name to the session roll route with the shell bearer', async () => {
    await upstream.upstreamReply(200, {
      session_id: 'session-7', roller_id: 'user-valeros', roller_name: 'Valeros the Bold',
      formula: '1d20', total: 17, rolls: [17], is_crit: false, is_fumble: false, roll_type: 'general',
    });
    const roller = await mount('Valeros the Bold');

    rollButton(roller)?.click();

    await expect.poll(() => shownTotal(roller)).toBe('17');
    const [request] = await upstream.upstreamRequests();
    expect(request.method).toBe('POST');
    expect(request.path).toBe('/api/v1/sessions/session-7/roll');
    expect(request.authorization).toBe(`Bearer ${TOKEN}`);
    expect(JSON.parse(request.body)).toEqual({ formula: '1d20', roller_name: 'Valeros the Bold', roll_type: 'general' });
  });

  it('shows the total of the server reply, not a total the browser computed', async () => {
    await upstream.upstreamReply(200, {
      session_id: 'session-7', roller_id: 'user-valeros', roller_name: 'Valeros the Bold',
      formula: '1d20', total: 1, rolls: [1], is_crit: false, is_fumble: true, roll_type: 'general',
    });
    const roller = await mount('Valeros the Bold');

    rollButton(roller)?.click();

    await expect.poll(() => shownTotal(roller)).toBe('1');
    expect(roller.shadowRoot?.querySelector('.banner-fumble')?.textContent).toContain('CRITICAL FUMBLE');
  });

  it('shows the failure text and no total when the server refuses the roll', async () => {
    await upstream.upstreamReply(403, { detail: 'Not allowed.' });
    const roller = await mount('Valeros the Bold');

    rollButton(roller)?.click();

    await expect.poll(() => alertText(roller)).toBe('Your account is not authorized for this dice roll.');
    expect(shownTotal(roller)).toBe('');
  });

  it('offers no roll and says a character must be bound when no character is bound', async () => {
    const roller = await mount('');

    expect(rollButton(roller)).toBeNull();
    expect(roller.shadowRoot?.querySelector('[role="status"]')?.textContent).toContain('A character must be bound');
    expect(await upstream.upstreamRequests()).toEqual([]);
  });
});
