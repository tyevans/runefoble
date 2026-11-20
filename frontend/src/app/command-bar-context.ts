/**
 * The speaker's token for the typed command bar (TASK-0945).
 *
 * The Watcher stages a move from the speaker's token cell (TASK-0942). The session view passes
 * the token of the active character and its shown cell to `<runefoble-command-bar>`. The cell
 * comes from the board's `tokens-changed` event, so it follows each confirmed move. A character
 * without a token on the board gives no token and no cell, and the bar is disabled.
 */

import type { BoardToken } from '@runefoble/board-state-ui';

export interface SpeakerTokenCell {
  tokenId: string | null;
  fromX: number | null;
  fromY: number | null;
}

const NO_TOKEN: SpeakerTokenCell = { tokenId: null, fromX: null, fromY: null };

/** The token of `characterId` on the shown board, with its cell. */
export function speakerTokenCell(tokens: BoardToken[], characterId: string | null | undefined): SpeakerTokenCell {
  if (!characterId) return NO_TOKEN;
  const token = tokens.find((t) => t.characterId === characterId);
  return token ? { tokenId: token.id, fromX: token.x, fromY: token.y } : NO_TOKEN;
}
