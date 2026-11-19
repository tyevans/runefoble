/**
 * DM battlemap set-up flow (TASK-0922).
 *
 * The DM creates the session board through `POST /api/v1/boards`, then places one token for
 * each seated character through `POST /api/v1/boards/{sessionId}/tokens`. board_state checks
 * `campaign.run_session` and the token permissions. The flow keeps no board state of its own:
 * the caller reads the board from the server after the flow ends.
 */

import { postJson, requestFailureMessage, type RequestOptions } from '@runefoble/ui-core';

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

interface CreatedBoard {
  cols: number;
  rows: number;
}

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

/** The body of `POST /api/v1/boards`. */
export function buildCreateBoardBody(req: BoardSetUpRequest): Record<string, unknown> {
  return {
    campaign_id: req.campaignId,
    session_id: req.sessionId,
    cols: req.cols ?? DEFAULT_BOARD_COLS,
    rows: req.rows ?? DEFAULT_BOARD_ROWS,
  };
}

/** The body of `POST /api/v1/boards/{sessionId}/tokens` for one seated character. */
export function buildPlacePartyTokenBody(seat: PartySeat, cell: GridCell): Record<string, unknown> {
  return {
    name: seat.characterName,
    token_type: 'pc',
    x: cell.x,
    y: cell.y,
    character_id: seat.characterId,
  };
}

/**
 * Creates the board, then places the party tokens in seat order. The first failed call stops
 * the flow, and its server message is returned. No call is retried and no value is invented.
 */
export async function setUpSessionBoard(req: BoardSetUpRequest, opts: RequestOptions = {}): Promise<BoardSetUpResult> {
  let board: CreatedBoard;
  try {
    board = await postJson<CreatedBoard>('/api/v1/boards', buildCreateBoardBody(req), opts);
  } catch (err) {
    return { ok: false, boardCreated: false, message: requestFailureMessage(err) };
  }
  let cells: GridCell[];
  try {
    cells = startCells(req.seats.length, board.cols, board.rows);
  } catch (err) {
    return { ok: false, boardCreated: true, message: (err as Error).message };
  }
  const tokensPath = `/api/v1/boards/${encodeURIComponent(req.sessionId)}/tokens`;
  for (const [index, seat] of req.seats.entries()) {
    try {
      await postJson(tokensPath, buildPlacePartyTokenBody(seat, cells[index]), opts);
    } catch (err) {
      return { ok: false, boardCreated: true, message: `${seat.characterName}: ${requestFailureMessage(err)}` };
    }
  }
  return { ok: true, placed: req.seats.length };
}
