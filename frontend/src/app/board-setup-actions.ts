/**
 * App Shell side of the DM battlemap set-up (TASK-0922).
 *
 * `<runefoble-board-empty>` creates the board and places the party tokens through the gateway.
 * When board_state holds a board, it dispatches `board-set-up`. The App Shell then tells the
 * other session clients through the `board_ready` frame, and reads the board from the server.
 * The App Shell never builds the board on the client side.
 */

import type { BoardSetUpDetail } from '@runefoble/board-state-ui';
import type { RunefobleApp } from '../runefoble-app.ts';

/** Announces the new board on the session socket, shows a token failure, and reads the board again. */
export function handleBoardSetUp(host: RunefobleApp, e: CustomEvent<BoardSetUpDetail>): void {
  const socket = host.sessionSocket.current;
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'board_ready', sessionId: e.detail.sessionId }));
  if (e.detail.failure) host.showToast(`The board is set up, but a token was not placed. ${e.detail.failure}`);
  host.reloadRouteData();
}

/** A `board_ready` frame for the open session reads the board again while this client has none. */
export function handleBoardReady(host: RunefobleApp, msg: { sessionId?: unknown }): void {
  if (msg.sessionId !== host.sessionId || host.boardKind !== 'no_board') return;
  host.reloadRouteData();
}
