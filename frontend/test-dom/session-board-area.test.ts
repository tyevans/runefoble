/**
 * Session board area before the first board read (Kind run 6). The live session view renders in a
 * real Chromium DOM. Until the board read answers, no `<runefoble-board>` mounts, so the page opens
 * no board socket before the board exists. The elements are not defined here, so none opens a socket.
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'lit';
import { renderSessionActive } from '../src/views/session-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';

function sessionApp(boardKind: 'loading' | 'no_board' | 'board'): RunefobleApp {
  return {
    boardKind,
    viewMode: 'party',
    campaignId: 'camp-1',
    sessionId: 'sess-1',
    campaignCapabilities: { run_session: false },
    characters: [],
    sessionSeats: [],
    sessionParticipants: [],
    tokens: [],
    events: [],
    boardCols: 10,
    boardRows: 10,
    activeCharacter: null,
    resolveActiveCharacter: () => null,
    getWebSocketUrl: () => 'ws://127.0.0.1:9/ws/boards/sess-1',
    sessionSocket: { current: null },
  } as unknown as RunefobleApp;
}

let host: HTMLElement | undefined;

function renderArea(boardKind: 'loading' | 'no_board' | 'board'): HTMLElement {
  host = document.createElement('div');
  document.body.append(host);
  render(renderSessionActive(sessionApp(boardKind)), host);
  return host;
}

afterEach(() => {
  host?.remove();
  host = undefined;
});

describe('session board area', () => {
  it('mounts no board and no empty state while the first board read is out', () => {
    const root = renderArea('loading');

    expect(root.querySelector('runefoble-board')).toBeNull();
    expect(root.querySelector('runefoble-board-empty')).toBeNull();
    expect(root.querySelector('.board-loading[role="status"]')?.textContent?.trim()).toBe('Loading the battlemap...');
  });

  it('mounts one board element when the read returns a board', () => {
    const root = renderArea('board');

    expect(root.querySelectorAll('runefoble-board')).toHaveLength(1);
    expect(root.querySelector('.board-loading')).toBeNull();
  });
});

describe('board tokens across App Shell renders (TASK-0938)', () => {
  const read = [{ id: 'tok-valeros', name: 'Valeros the Bold', x: 0, y: 0 }];

  it('a render with the same board read keeps a move that the board applied from its socket', () => {
    const app = sessionApp('board');
    (app as { tokens: unknown }).tokens = read;
    host = document.createElement('div');
    document.body.append(host);
    render(renderSessionActive(app), host);
    const board = host.querySelector('runefoble-board') as unknown as { tokens: unknown[] };
    const moved = [{ ...read[0], x: 3, y: 3 }];
    board.tokens = moved;

    // Another shell change, for example a chronicle frame, renders the view again.
    render(renderSessionActive(app), host);

    expect(board.tokens).toBe(moved);
  });

  it('a new board read replaces the board tokens', () => {
    const app = sessionApp('board');
    (app as { tokens: unknown }).tokens = read;
    host = document.createElement('div');
    document.body.append(host);
    render(renderSessionActive(app), host);
    const board = host.querySelector('runefoble-board') as unknown as { tokens: unknown[] };
    board.tokens = [{ ...read[0], x: 3, y: 3 }];

    const nextRead = [{ ...read[0], x: 5, y: 5 }];
    (app as { tokens: unknown }).tokens = nextRead;
    render(renderSessionActive(app), host);

    expect(board.tokens).toBe(nextRead);
  });
});
