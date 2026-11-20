/**
 * App Shell to microfrontend session events (TASK-0826, audit F-07).
 *
 * The shell forwards live session messages as documented window events. Service elements
 * subscribe to those events. The tests send a session message through the shell router and
 * check what the mounted service element shows. No test queries a service shadow root.
 * Event names: docs/reference/microfrontend-architecture.md, "Session Mesh Events".
 *
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import '@runefoble/board-state-ui/runefoble-board';
import '@runefoble/board-state-ui/runefoble-dice-tray-3d';
import '@runefoble/game-session-ui/runefoble-initiative-tracker';
import '@runefoble/the-watcher-ui/runefoble-dm-whisper-bar';
import { handleSessionMessage } from '../src/app/session-messages.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';

const HOST = { events: [] } as unknown as RunefobleApp;

async function mount<T extends HTMLElement>(tag: string, props: Record<string, unknown> = {}): Promise<T> {
  const el = document.createElement(tag) as T & { updateComplete?: Promise<boolean> };
  Object.assign(el, props);
  document.body.append(el);
  await el.updateComplete;
  return el;
}

afterEach(() => {
  document.body.replaceChildren();
  vi.restoreAllMocks();
});

describe('dice_rolled session message', () => {
  it('adds one chronicle row for each roll, with the roller and the server total', () => {
    const host = { events: [] } as unknown as RunefobleApp;

    handleSessionMessage(host, { type: 'dice_rolled', rollerName: 'Sarah of the Mists', formula: '1d20', total: 14, rolls: [14] });
    handleSessionMessage(host, { type: 'dice_rolled', rollerName: 'Sarah of the Mists', formula: '1d20', total: 3, rolls: [3] });

    const rows = (host as unknown as { events: Array<{ speaker: string; text: string; actionType: string }> }).events;
    expect(rows.map((row) => [row.speaker, row.text, row.actionType])).toEqual([
      ['Sarah of the Mists', '1d20 = 14', 'dice_roll'],
      ['Sarah of the Mists', '1d20 = 3', 'dice_roll'],
    ]);
  });

  it('rolls a mounted 3D dice tray', async () => {
    const tray = await mount<HTMLElement>('runefoble-dice-tray-3d');
    const rolled = vi.fn();
    tray.addEventListener('dice-rolled', rolled);

    handleSessionMessage(HOST, { type: 'dice_rolled', diceType: 'd20', total: 12 });

    expect(rolled).toHaveBeenCalledTimes(1);
    expect((rolled.mock.calls[0][0] as CustomEvent).detail.targetFaceValue).toBe(12);
  });

  it('sends the roll to a mounted board', async () => {
    const board = await mount<HTMLElement & { roll3DDice: (dice: unknown) => void }>('runefoble-board', { cols: 4, rows: 4, tokens: [] });
    const roll = vi.spyOn(board, 'roll3DDice').mockImplementation(() => undefined);
    const dice = { diceType: 'd20', face: 9 };

    handleSessionMessage(HOST, { type: 'dice_rolled', dice });

    expect(roll).toHaveBeenCalledWith(dice);
  });
});

describe('turn_advanced session message', () => {
  it('moves a mounted initiative tracker to the active combatant and round', async () => {
    const tracker = await mount<HTMLElement & { activeCombatantId: string | null; roundNumber: number }>('runefoble-initiative-tracker');

    handleSessionMessage(HOST, { type: 'turn_advanced', activeCombatantId: 'combatant-2', roundNumber: 3 });

    expect(tracker.activeCombatantId).toBe('combatant-2');
    expect(tracker.roundNumber).toBe(3);
  });

  it('marks the active turn token on a mounted board', async () => {
    const board = await mount<HTMLElement & { activeTurnTokenId: string | null }>('runefoble-board', { cols: 4, rows: 4, tokens: [] });

    handleSessionMessage(HOST, { type: 'turn_advanced', activeCombatantId: 'token-7' });

    expect(board.activeTurnTokenId).toBe('token-7');
  });
});

describe('aoe_placed and spell_vfx session messages', () => {
  it('shows an incoming AoE template on a mounted board', async () => {
    const board = await mount<HTMLElement & { activeAoE: unknown }>('runefoble-board', { cols: 4, rows: 4, tokens: [] });
    const template = { shape: 'sphere', originX: 1, originY: 2, directionDeg: 0, radiusFt: 10 };

    handleSessionMessage(HOST, { type: 'aoe_placed', template });

    expect(board.activeAoE).toEqual(template);
  });

  it('triggers spell VFX on a mounted board', async () => {
    const board = await mount<HTMLElement & { triggerSpellVFX: (params: unknown) => void }>('runefoble-board', { cols: 4, rows: 4, tokens: [] });
    const trigger = vi.spyOn(board, 'triggerSpellVFX');
    const vfx = { element: 'fire', archetype: 'burst' };

    handleSessionMessage(HOST, { type: 'spell_vfx', vfx });

    expect(trigger).toHaveBeenCalledWith(vfx);
  });
});

describe('dm_whisper session message', () => {
  it('adds the whisper to a mounted whisper bar', async () => {
    const bar = await mount<HTMLElement & { whispers: Array<{ content: string }> }>('runefoble-dm-whisper-bar');

    handleSessionMessage(HOST, { type: 'dm_whisper', whisper_id: 'w-1', whisper_type: 'narrative_secret', content: 'The door hums.' });

    expect(bar.whispers.at(-1)?.content).toBe('The door hums.');
  });
});
