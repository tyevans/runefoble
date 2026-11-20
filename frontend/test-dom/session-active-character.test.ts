/**
 * The live session view shows only the bound character (TASK-0972).
 *
 * The character card, the roller name and the stance control read the bound character. A caller
 * with no bound character sees the empty state and no roller name. Governing ADRs: ADR-0004,
 * ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'lit';
import { renderSessionActive } from '../src/views/session-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';
import { pickActiveCharacter } from '../src/app/active-character.ts';

const valeros = { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', level: 4, currentHp: 38, maxHp: 45, armorClass: 18, campaignId: '4', ownerId: 'user-alice' };
const kyra = { id: 'char-kyra', name: 'Kyra the Sun Maiden', characterClass: 'Cleric', level: 4, currentHp: 28, maxHp: 32, armorClass: 16, campaignId: '4', ownerId: 'user-bob' };

function sessionApp(currentUserId: string): RunefobleApp {
  const characters = [kyra, valeros];
  const bind = () => pickActiveCharacter(characters, '4', currentUserId, null);
  return {
    boardKind: 'loading',
    viewMode: 'party',
    sessionStatus: 'active',
    campaignId: '4',
    sessionId: 'sess-1',
    currentUserId,
    campaignCapabilities: { run_session: false, play: true },
    characters,
    sessionSeats: [],
    sessionParticipants: [],
    tokens: [],
    events: [],
    atmosphere: {},
    isListening: false,
    activeCharacter: bind(),
    resolveActiveCharacter: bind,
    getWebSocketUrl: () => 'ws://127.0.0.1:9/ws/boards/sess-1',
    sessionSocket: { current: null },
  } as unknown as RunefobleApp;
}

let host: HTMLElement | undefined;

function renderView(app: RunefobleApp): HTMLElement {
  host = document.createElement('div');
  document.body.append(host);
  render(renderSessionActive(app), host);
  return host;
}

afterEach(() => {
  host?.remove();
  host = undefined;
});

describe('session view binds the caller character', () => {
  it('binds each caller to the caller own character, never to another player', () => {
    const root = renderView(sessionApp('user-bob'));

    const card = root.querySelector('runefoble-character-card') as any;
    expect(card?.characterName).toBe('Kyra the Sun Maiden');
  });

  it('shows the bound character card and names the roller after it', () => {
    const root = renderView(sessionApp('user-alice'));

    const card = root.querySelector('runefoble-character-card') as any;
    expect(card?.characterName).toBe('Valeros of Korvosa');
    const dice = root.querySelector('runefoble-plugin-slot[slot-id="dice-panel"]') as any;
    expect(dice?.pluginProps?.['default-dice-roller']?.rollerName).toBe('Valeros of Korvosa');
  });

  it('shows the empty state and no roller name when the caller has no bound character', () => {
    const root = renderView(sessionApp('user-carol'));

    expect(root.querySelector('runefoble-character-card')).toBeNull();
    expect(root.querySelector('[data-testid="active-character-empty"]')).not.toBeNull();
    const dice = root.querySelector('runefoble-plugin-slot[slot-id="dice-panel"]') as any;
    expect(dice?.pluginProps?.['default-dice-roller']?.rollerName).toBe('');
  });
});
