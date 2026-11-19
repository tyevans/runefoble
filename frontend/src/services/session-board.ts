/**
 * Session board read result (TASK-0906).
 *
 * A session can exist before its board. board_state answers 404 until a board is created.
 * The App Shell reads that answer as `no_board` and still renders the other session panels.
 */

import type { BoardToken } from '@runefoble/board-state-ui';

export interface LoadedBoard {
  kind: 'board';
  cols: number;
  rows: number;
  tokens: BoardToken[];
}

export interface NoBoard {
  kind: 'no_board';
}

export type SessionBoard = LoadedBoard | NoBoard;
