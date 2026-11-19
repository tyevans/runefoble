/**
 * App Shell side of the DM battlemap set-up (TASK-0922).
 *
 * After `<runefoble-board-empty>` reports `board-set-up`, the App Shell sends the `board_ready`
 * frame on the session socket and reads the board again. A `board_ready` frame makes a client
 * without a board read the board again. The socket is faked at the browser boundary only.
 * Governing ADRs: ADR-0013, ADR-0015.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { handleBoardSetUp } from '../../src/app/board-setup-actions.ts';
import { handleSessionMessage } from '../../src/app/session-messages.ts';
import type { RunefobleApp } from '../../src/runefoble-app.ts';

const OPEN = 1;
(globalThis as any).WebSocket ??= { OPEN };

function host(boardKind: 'board' | 'no_board') {
  const sent: string[] = [];
  const toasts: string[] = [];
  let reloads = 0;
  const app = {
    sessionId: 'sess-1',
    boardKind,
    sessionSocket: { current: { readyState: (globalThis as any).WebSocket.OPEN, send: (f: string) => sent.push(f) } },
    showToast: (m: string) => toasts.push(m),
    reloadRouteData: () => { reloads += 1; },
  } as unknown as RunefobleApp;
  return { app, sent, toasts, reloads: () => reloads };
}

function setUpEvent(failure: string | null): CustomEvent {
  return { detail: { sessionId: 'sess-1', failure } } as CustomEvent;
}

describe('battlemap set-up in the App Shell', () => {
  it('announces the board on the session socket and reads the board again', () => {
    const h = host('no_board');
    handleBoardSetUp(h.app, setUpEvent(null));
    assert.deepEqual(h.sent.map((f) => JSON.parse(f)), [{ type: 'board_ready', sessionId: 'sess-1' }]);
    assert.equal(h.reloads(), 1);
    assert.deepEqual(h.toasts, []);
  });

  it('shows the owner message when a token was not placed', () => {
    const h = host('no_board');
    handleBoardSetUp(h.app, setUpEvent('Sarah: Forbidden'));
    assert.equal(h.reloads(), 1);
    assert.match(h.toasts[0], /a token was not placed\. Sarah: Forbidden/);
  });

  it('reads the board again on a board_ready frame while the client has no board', () => {
    const h = host('no_board');
    handleSessionMessage(h.app, { type: 'board_ready', sessionId: 'sess-1' });
    assert.equal(h.reloads(), 1);
  });

  it('ignores board_ready for another session or when a board is shown', () => {
    const other = host('no_board');
    handleSessionMessage(other.app, { type: 'board_ready', sessionId: 'sess-2' });
    const loaded = host('board');
    handleSessionMessage(loaded.app, { type: 'board_ready', sessionId: 'sess-1' });
    assert.equal(other.reloads() + loaded.reloads(), 0);
  });
});
