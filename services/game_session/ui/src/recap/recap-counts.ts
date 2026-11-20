/**
 * Recap counts for an ended session (TASK-0953). The counts read the chronicle lines the recap
 * shows. A line counts once, by its kind: a dice roll, a token move, or a stand-in action.
 */

/** One chronicle line that the recap lists. The App Shell feed row has this shape. */
export interface RecapEntry {
  id: string;
  speaker: string;
  text: string;
  timestamp?: string;
  source?: string;
  actionType?: string;
}

export interface RecapCounts {
  diceRolls: number;
  tokenMoves: number;
  standInActions: number;
}

/** Counts the dice rolls, token moves and stand-in actions of the recap lines. */
export function recapCounts(entries: readonly RecapEntry[]): RecapCounts {
  return {
    diceRolls: entries.filter((entry) => entry.actionType === 'dice_roll').length,
    tokenMoves: entries.filter((entry) => entry.actionType === 'board_move').length,
    standInActions: entries.filter((entry) => entry.source === 'stand_in').length,
  };
}
