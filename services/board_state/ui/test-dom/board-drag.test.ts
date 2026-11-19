/**
 * Token drag and refused moves on `<runefoble-board>` (defect found on Kind).
 * The element runs in headless Chromium. Playwright drives a real mouse drag and a real tap.
 * The test reads the dispatched events and the rendered board, as a user and the host would.
 * Server frames go in through `handleIncomingSocketMessage`, the handler of the board socket.
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { userEvent } from 'vitest/browser';
import '../src/runefoble-board.ts';
import type { RunefobleBoard } from '../src/runefoble-board.ts';

interface Move { tokenId: string; toX: number; toY: number }

async function mount(): Promise<RunefobleBoard> {
  const el = document.createElement('runefoble-board');
  el.cols = 10;
  el.rows = 10;
  el.fogOfWar = true;
  el.tokens = [
    { id: 'tok-valeros', name: 'Valeros the Bold', x: 0, y: 0 },
    { id: 'tok-sarah', name: 'Sarah of the Mists', x: 1, y: 0 },
  ];
  document.body.append(el);
  await el.updateComplete;
  return el;
}

function token(el: RunefobleBoard, name: string): HTMLElement {
  const found = el.shadowRoot?.querySelector<HTMLElement>(`.token[title^="${name}"]`);
  if (!found) throw new Error(`No token for ${name}`);
  return found;
}

function cell(el: RunefobleBoard, x: number, y: number): HTMLElement {
  const cells = Array.from(el.shadowRoot?.querySelectorAll<HTMLElement>('.cell') ?? []);
  const found = cells.find((c) => c.querySelector('.coord-label')?.textContent?.trim() === `${x},${y}`);
  if (!found) throw new Error(`No cell ${x},${y}`);
  return found;
}

function recorded(el: RunefobleBoard, name: string): Move[] {
  const moves: Move[] = [];
  el.addEventListener(name, (e) => moves.push((e as CustomEvent<Move>).detail));
  return moves;
}

function alertText(el: RunefobleBoard): string | null {
  return el.shadowRoot?.querySelector('[role="alert"]')?.textContent?.trim() ?? null;
}

afterEach(() => document.querySelectorAll('runefoble-board').forEach((el) => el.remove()));

describe('runefoble-board token drag', () => {
  it('sends one move for a drag, and the click that ends the drag sends no move back', async () => {
    const el = await mount();
    const moves = recorded(el, 'move-token');

    await userEvent.dragAndDrop(token(el, 'Valeros the Bold'), cell(el, 3, 3));
    await el.updateComplete;

    expect(moves).toEqual([{ tokenId: 'tok-valeros', toX: 3, toY: 3 }]);
  });

  it('shows the refusal when the board socket is not open', async () => {
    const el = await mount();
    const rejected = recorded(el, 'move-rejected');

    await userEvent.dragAndDrop(token(el, 'Valeros the Bold'), cell(el, 3, 3));
    await el.updateComplete;

    expect(rejected).toHaveLength(1);
    expect(alertText(el)).toBe('The board connection is not open, so the move was not sent.');
  });

  it('keeps the radial menu open after a tap on a token', async () => {
    const el = await mount();
    const moves = recorded(el, 'move-token');

    await userEvent.click(token(el, 'Valeros the Bold'));
    await el.updateComplete;

    expect(el.shadowRoot?.querySelector('runefoble-radial-menu')).not.toBeNull();
    expect(moves).toEqual([]);
  });
});

describe('runefoble-board server error frames', () => {
  it('shows the message of a refused move, and the token stays on its cell', async () => {
    const el = await mount();

    el.handleIncomingSocketMessage({
      type: 'error',
      code: 'PERMISSION_DENIED',
      message: "'confirm_move' on token 'tok-valeros' needs board_token.move",
      status: 403,
      action: 'confirm_move',
      token_id: 'tok-valeros',
    });
    await el.updateComplete;

    expect(alertText(el)).toBe("confirm_move refused: 'confirm_move' on token 'tok-valeros' needs board_token.move");
    expect(cell(el, 0, 0).querySelector('.token[title^="Valeros the Bold"]')).not.toBeNull();
  });
});

describe('runefoble-board connected snapshot', () => {
  it('shows the token cells of the connected frame, so a move before the socket opened is shown', async () => {
    const el = await mount();

    el.handleIncomingSocketMessage({
      type: 'connected',
      session_id: 'sess-1',
      tokens: {
        'tok-valeros': { token_id: 'tok-valeros', name: 'Valeros the Bold', x: 3, y: 3, vision_radius: 2 },
        'tok-sarah': { token_id: 'tok-sarah', name: 'Sarah of the Mists', x: 1, y: 0, vision_radius: 2 },
      },
    });
    await el.updateComplete;

    expect(cell(el, 3, 3).querySelector('.token[title^="Valeros the Bold"]')).not.toBeNull();
    expect(cell(el, 0, 0).querySelector('.token')).toBeNull();
    expect(cell(el, 1, 0).querySelector('.token[title^="Sarah of the Mists"]')).not.toBeNull();
  });
});
