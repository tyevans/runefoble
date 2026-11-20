/**
 * Dice roll request over the shared UI transport (TASK-0951).
 *
 * The owner evaluates every roll. The browser sends the formula and the character name, and
 * it shows the reply. No call sends a caller-asserted identity. The bearer comes from the
 * shared auth source, and the gateway reads the roller from it. A failed call rejects with the
 * error, so the caller shows the server message.
 */

import { postJson, type AuthSource } from '@runefoble/ui-core';

/** The server reply for one stored roll (`RollDiceResponse` in game_session). */
export interface DiceRollReply {
  session_id: string;
  roller_id: string;
  roller_name: string;
  formula: string;
  total: number;
  rolls: number[];
  is_crit: boolean;
  is_fumble: boolean;
  roll_type: string;
}

export interface DiceRollContext {
  /** API base URL. Empty means the page origin. */
  apiBase: string;
  /** The shared auth source. */
  auth: AuthSource;
}

/** Sends one roll to the session and resolves with the stored roll. */
export function postDiceRoll(
  ctx: DiceRollContext,
  sessionId: string,
  roll: { formula: string; rollerName: string },
): Promise<DiceRollReply> {
  return postJson<DiceRollReply>(
    `/api/v1/sessions/${encodeURIComponent(sessionId)}/roll`,
    { formula: roll.formula, roller_name: roll.rollerName, roll_type: 'general' },
    { apiBase: ctx.apiBase, auth: ctx.auth },
  );
}
