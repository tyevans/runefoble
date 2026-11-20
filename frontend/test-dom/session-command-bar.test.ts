/**
 * The typed command bar in the live session view (TASK-0945). The view renders in a real
 * Chromium DOM. The service elements are not defined here, so the test reads the properties
 * that the view passes to `<runefoble-command-bar>`. The board's `tokens-changed` event gives
 * the cell of the caller's token. Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'lit';
import { renderSessionActive } from '../src/views/session-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';

const VALEROS = { id: 'char-valeros', name: 'Valeros the Bold', characterClass: 'Fighter', level: 1, currentHp: 24, maxHp: 24, armorClass: 16 };

function sessionApp(): RunefobleApp {
  return {
    boardKind: 'board',
    viewMode: 'party',
    campaignId: 'camp-1',
    sessionId: 'sess-1',
    campaignCapabilities: { run_session: false },
    characters: [VALEROS],
    sessionSeats: [],
    sessionParticipants: [],
    tokens: [{ id: 'tok-valeros', name: 'Valeros the Bold', x: 0, y: 0, characterId: 'char-valeros' }],
    shownTokens: [],
    commandStatus: { kind: 'idle' },
    events: [],
    voiceUtterance: { sending: false, transcript: '', watcherError: '', uploadError: '' },
    boardCols: 10,
    boardRows: 8,
    activeCharacter: VALEROS,
    resolveActiveCharacter: () => VALEROS,
    getWebSocketUrl: () => 'ws://127.0.0.1:9/ws/boards/sess-1',
    sessionSocket: { current: null },
  } as unknown as RunefobleApp;
}

let host: HTMLElement | undefined;

afterEach(() => {
  host?.remove();
  host = undefined;
});

type Bar = HTMLElement & Record<string, unknown>;

describe('session command bar', () => {
  it('passes the cell that the board shows for the caller token', () => {
    const app = sessionApp();
    host = document.createElement('div');
    document.body.append(host);
    render(renderSessionActive(app), host);
    const board = host.querySelector('runefoble-board') as HTMLElement;

    board.dispatchEvent(new CustomEvent('tokens-changed', {
      detail: { tokens: [{ id: 'tok-valeros', name: 'Valeros the Bold', x: 3, y: 2, characterId: 'char-valeros' }] },
      bubbles: true,
      composed: true,
    }));
    render(renderSessionActive(app), host);

    const bar = host.querySelector('runefoble-command-bar') as Bar;
    expect(bar).not.toBeNull();
    expect([bar.speakerId, bar.speakerName, bar.tokenId, bar.fromX, bar.fromY]).toEqual(['char-valeros', 'Valeros the Bold', 'tok-valeros', 3, 2]);
    expect([bar.sessionId, bar.campaignId, bar.gridCols, bar.gridRows]).toEqual(['sess-1', 'camp-1', 10, 8]);
  });

  it('passes no token while the board shows no token of the caller', () => {
    host = document.createElement('div');
    document.body.append(host);
    render(renderSessionActive(sessionApp()), host);

    const bar = host.querySelector('runefoble-command-bar') as Bar;
    expect([bar.tokenId, bar.fromX, bar.fromY]).toEqual([null, null, null]);
  });
});
