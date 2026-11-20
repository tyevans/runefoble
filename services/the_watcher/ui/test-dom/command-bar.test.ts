/**
 * `<runefoble-command-bar>` in headless Chromium (TASK-0945).
 * The test types and presses keys as a player does. It reads the emitted `speak-command`
 * events and the rendered bar, as the host and the player do. Governing ADRs: ADR-0004,
 * ADR-0013, ADR-0014, ADR-0022 (c).
 */

import { afterEach, describe, expect, it } from 'vitest';
import { userEvent } from 'vitest/browser';
import '../src/runefoble-command-bar.ts';
import type { RunefobleCommandBar } from '../src/runefoble-command-bar.ts';
import type { SpeakCommandBody } from '../src/command-bar-body.ts';

async function mount(token: { tokenId: string | null; fromX: number | null; fromY: number | null }): Promise<RunefobleCommandBar> {
  const el = document.createElement('runefoble-command-bar');
  Object.assign(el, {
    sessionId: 'session-tomb-14',
    campaignId: 'campaign-4',
    speakerId: 'char-valeros',
    speakerName: 'Valeros the Bold',
    gridCols: 10,
    gridRows: 10,
    ...token,
  });
  document.body.append(el);
  await el.updateComplete;
  return el;
}

const ON_BOARD = { tokenId: 'tok-valeros', fromX: 4, fromY: 2 };

function input(el: RunefobleCommandBar): HTMLInputElement {
  const found = el.shadowRoot?.querySelector<HTMLInputElement>('input');
  if (!found) throw new Error('No command input');
  return found;
}

function sendButton(el: RunefobleCommandBar): HTMLButtonElement {
  const found = el.shadowRoot?.querySelector<HTMLButtonElement>('button');
  if (!found) throw new Error('No Send button');
  return found;
}

function statusText(el: RunefobleCommandBar): string | null {
  return el.shadowRoot?.querySelector('.status')?.textContent?.trim() ?? null;
}

function recorded(el: RunefobleCommandBar): SpeakCommandBody[] {
  const sent: SpeakCommandBody[] = [];
  el.addEventListener('speak-command', (e) => sent.push((e as CustomEvent<SpeakCommandBody>).detail));
  return sent;
}

afterEach(() => document.querySelectorAll('runefoble-command-bar').forEach((el) => el.remove()));

describe('runefoble-command-bar', () => {
  it('emits one speak-command with the token cell when the player presses Enter', async () => {
    const el = await mount(ON_BOARD);
    const sent = recorded(el);

    await userEvent.type(input(el), 'move 2 squares west{Enter}');

    expect(sent).toEqual([{
      speaker_id: 'char-valeros',
      speaker_name: 'Valeros the Bold',
      transcript: 'move 2 squares west',
      session_id: 'session-tomb-14',
      campaign_id: 'campaign-4',
      token_id: 'tok-valeros',
      from_x: 4,
      from_y: 2,
      grid_cols: 10,
      grid_rows: 10,
    }]);
  });

  it('emits the command when the player clicks Send', async () => {
    const el = await mount(ON_BOARD);
    const sent = recorded(el);

    await userEvent.type(input(el), 'move north');
    await userEvent.click(sendButton(el));

    expect(sent.map((b) => b.transcript)).toEqual(['move north']);
  });

  it('disables the input and says why when the speaker has no token on the board', async () => {
    const el = await mount({ tokenId: null, fromX: null, fromY: null });

    expect(input(el).disabled).toBe(true);
    expect(sendButton(el).disabled).toBe(true);
    expect(statusText(el)).toBe('No character token is on the board.');
  });

  it('shows the reply and clears the typed text', async () => {
    const el = await mount(ON_BOARD);
    await userEvent.type(input(el), 'dance nicely');

    el.status = { kind: 'reply', text: 'Not understood.' };
    await el.updateComplete;

    expect(statusText(el)).toBe('Not understood.');
    expect(input(el).value).toBe('');
  });

  it('shows the error and keeps the typed text', async () => {
    const el = await mount(ON_BOARD);
    await userEvent.type(input(el), 'move 2 squares west');

    el.status = { kind: 'error', text: 'HTTP 503: The Watcher is unavailable.' };
    await el.updateComplete;

    expect(el.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim()).toBe('HTTP 503: The Watcher is unavailable.');
    expect(input(el).value).toBe('move 2 squares west');
  });

  it('sends no second command while one is out', async () => {
    const el = await mount(ON_BOARD);
    const sent = recorded(el);
    await userEvent.type(input(el), 'move north');
    el.status = { kind: 'sending' };
    await el.updateComplete;

    await userEvent.type(input(el), '{Enter}');

    expect(sent).toEqual([]);
    expect(statusText(el)).toBe('Sending the command...');
  });
});
