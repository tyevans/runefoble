/**
 * DM battlemap set-up flow (TASK-0922, TASK-0928).
 *
 * The DM sends one `POST /api/v1/boards` call. Its body holds the grid and one token for each
 * seated character. The gateway creates the board, places the tokens in order, and then sends
 * `board_ready` to the session sockets once. Thus a client that reads the board after that frame
 * gets the party tokens. board_state checks `campaign.run_session` and the token permissions.
 * The flow keeps no board state of its own: the caller reads the board from the server.
 */

import { HttpError, isRecord, postJson, requestFailureMessage, type RequestOptions } from '@runefoble/ui-core';

/** The default grid of a new session board, in cells. */
export const DEFAULT_BOARD_COLS = 10;
export const DEFAULT_BOARD_ROWS = 10;

/** One seated character of the session. The token takes the character name. */
export interface PartySeat {
  characterId: string;
  characterName: string;
}

export interface BoardSetUpRequest {
  campaignId: string;
  sessionId: string;
  seats: PartySeat[];
  cols?: number;
  rows?: number;
}

export interface GridCell {
  x: number;
  y: number;
}

/**
 * The outcome of the set-up flow. `boardCreated` tells the caller whether board_state now holds
 * a board. A failure after the board exists still needs a board read, because some tokens can be placed.
 */
export type BoardSetUpResult =
  | { ok: true; placed: number }
  | { ok: false; boardCreated: boolean; message: string };

/**
 * Returns `count` free start cells in row order, from the top-left cell. A cell in `occupied` is
 * not free. Throws a RangeError when the grid has fewer free cells than `count`.
 */
export function startCells(count: number, cols: number, rows: number, occupied: GridCell[] = []): GridCell[] {
  const taken = new Set(occupied.map((c) => `${c.x},${c.y}`));
  const cells: GridCell[] = [];
  for (let y = 0; y < rows && cells.length < count; y += 1) {
    for (let x = 0; x < cols && cells.length < count; x += 1) {
      if (!taken.has(`${x},${y}`)) cells.push({ x, y });
    }
  }
  if (cells.length < count) throw new RangeError(`The ${cols}x${rows} grid has no free start cell for ${count} tokens.`);
  return cells;
}

/** The body of `POST /api/v1/boards`: the grid, and one party token for each seat. */
export function buildSetUpBoardBody(req: BoardSetUpRequest, cells: GridCell[]): Record<string, unknown> {
  return {
    campaign_id: req.campaignId,
    session_id: req.sessionId,
    cols: req.cols ?? DEFAULT_BOARD_COLS,
    rows: req.rows ?? DEFAULT_BOARD_ROWS,
    tokens: req.seats.map((seat, index) => buildPartyTokenBody(seat, cells[index])),
  };
}

/** One party token of the set-up body, for one seated character. */
export function buildPartyTokenBody(seat: PartySeat, cell: GridCell): Record<string, unknown> {
  return {
    name: seat.characterName,
    token_type: 'pc',
    x: cell.x,
    y: cell.y,
    character_id: seat.characterId,
  };
}

/** True when the gateway reports that the board exists after a refused or failed token. */
function boardCreatedIn(err: unknown): boolean {
  return err instanceof HttpError && isRecord(err.body) && err.body.board_created === true;
}

/**
 * Sends the set-up call. A failed call returns the server message. When the gateway reports
 * `board_created`, the board exists with the tokens before the failed one. No call is retried
 * and no value is invented.
 */
export async function setUpSessionBoard(req: BoardSetUpRequest, opts: RequestOptions = {}): Promise<BoardSetUpResult> {
  let cells: GridCell[];
  try {
    cells = startCells(req.seats.length, req.cols ?? DEFAULT_BOARD_COLS, req.rows ?? DEFAULT_BOARD_ROWS);
  } catch (err) {
    return { ok: false, boardCreated: false, message: (err as Error).message };
  }
  try {
    await postJson('/api/v1/boards', buildSetUpBoardBody(req, cells), opts);
  } catch (err) {
    return { ok: false, boardCreated: boardCreatedIn(err), message: requestFailureMessage(err) };
  }
  return { ok: true, placed: req.seats.length };
}
