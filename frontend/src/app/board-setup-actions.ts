/**
 * App Shell side of the DM battlemap set-up (TASK-0922).
 *
 * `<runefoble-board-empty>` creates the board and places the party tokens through the gateway.
 * When board_state holds a board, it dispatches `board-set-up`. The App Shell then reads the
 * board from the server. The gateway board create route sends the `board_ready` frame to the
 * other session clients (TASK-0922). A client never sends that frame.
 * The App Shell never builds the board on the client side.
 */

import type { BoardSetUpDetail } from '@runefoble/board-state-ui';
import type { RunefobleApp } from '../runefoble-app.ts';

/** Shows a token failure and reads the board again. */
export function handleBoardSetUp(host: RunefobleApp, e: CustomEvent<BoardSetUpDetail>): void {
  if (e.detail.failure) host.showToast(`The board is set up, but a token was not placed. ${e.detail.failure}`);
  host.reloadRouteData();
}

/**
 * A `board_ready` frame for the open session reads the board again while this client has none.
 * While the first read is still out (`loading`), it can answer 404 from before the set-up, so
 * the client reads again.
 */
export function handleBoardReady(host: RunefobleApp, msg: { sessionId?: unknown }): void {
  if (msg.sessionId !== host.sessionId || host.boardKind === 'board') return;
  host.reloadRouteData();
}
