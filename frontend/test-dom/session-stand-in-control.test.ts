/**
 * The stance drawer button follows the caller seat (TASK-0974).
 *
 * game_session holds the stand-in state on the seat. The live session view shows the stance
 * control only while the caller seat is an active stand-in. The character record flag is not read
 * for this, so a stale record cannot show the control. Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'lit';
import { renderSessionActive } from '../src/views/session-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';
import { pickActiveCharacter } from '../src/app/active-character.ts';

const valeros = { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', level: 4, currentHp: 38, maxHp: 45, armorClass: 18, campaignId: '4', ownerId: 'user-alice', isAiStandIn: false };

function sessionApp(standInActive: boolean, recordFlag = false): RunefobleApp {
  const characters = [{ ...valeros, isAiStandIn: recordFlag }];
  const participants = [{ userId: 'user-alice', characterId: 'char-valeros', characterName: 'Valeros of Korvosa', isStandInActive: standInActive }];
  return {
    boardKind: 'loading',
    viewMode: 'party',
    sessionStatus: 'active',
    campaignId: '4',
    sessionId: 'sess-1',
    currentUserId: 'user-alice',
    campaignCapabilities: { run_session: false, play: true },
    characters,
    sessionSeats: [],
    sessionParticipants: participants,
    tokens: [],
    events: [],
    atmosphere: {},
    isListening: false,
    activeCharacter: pickActiveCharacter(characters, '4', 'user-alice', null),
    resolveActiveCharacter: () => null,
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

describe('the stance drawer button follows the caller seat', () => {
  it('shows Stance Directives when the caller seat is an active stand-in', () => {
    const root = renderView(sessionApp(true));

    expect(root.querySelector('.btn-toggle-directive')?.textContent).toContain('Stance Directives');
    expect((root.querySelector('runefoble-character-card') as any)?.isAiStandIn).toBe(true);
  });

  it('hides the button when the caller seat is not a stand-in', () => {
    const root = renderView(sessionApp(false));

    expect(root.querySelector('.btn-toggle-directive')).toBeNull();
    expect((root.querySelector('runefoble-character-card') as any)?.isAiStandIn).toBe(false);
  });

  it('ignores a stand-in flag on the character record when the seat is not a stand-in', () => {
    const root = renderView(sessionApp(false, true));

    expect(root.querySelector('.btn-toggle-directive')).toBeNull();
  });
});
