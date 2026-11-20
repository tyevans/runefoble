/**
 * The body of one typed command, and the status that the command bar shows (TASK-0945).
 *
 * `<runefoble-command-bar>` emits the body as the `speak-command` event. The host posts it to
 * `POST /api/v1/watcher/speak-and-act`. The Watcher needs the speaker's token and its cell to
 * stage a move, so a bar without a token cell builds no body (TASK-0942).
 */

/** What the bar knows about the speaker and the board. */
export interface CommandBarContext {
  sessionId: string;
  campaignId: string;
  speakerId: string;
  speakerName: string;
  tokenId: string | null;
  fromX: number | null;
  fromY: number | null;
  gridCols: number;
  gridRows: number;
}

/** The JSON body of `POST /api/v1/watcher/speak-and-act` (The Watcher `SpeechInputRequest`). */
export interface SpeakCommandBody {
  speaker_id: string;
  speaker_name: string;
  transcript: string;
  session_id: string;
  campaign_id: string;
  token_id: string;
  from_x: number;
  from_y: number;
  grid_cols: number;
  grid_rows: number;
}

/** What the bar shows under the input. The host sets it. */
export type CommandBarStatus =
  | { kind: 'idle' }
  | { kind: 'sending' }
  | { kind: 'reply'; text: string }
  | { kind: 'error'; text: string };

export const IDLE_COMMAND_STATUS: CommandBarStatus = { kind: 'idle' };
export const NO_TOKEN_MESSAGE = 'No character token is on the board.';

/** True when the context has the speaker's token and a whole-number cell for it. */
export function hasTokenCell(ctx: CommandBarContext): boolean {
  return Boolean(ctx.tokenId) && Number.isInteger(ctx.fromX) && Number.isInteger(ctx.fromY);
}

/**
 * Builds the body for one typed command. Returns null for a blank transcript or when the
 * speaker has no token cell. The transcript is sent without its outer spaces.
 */
export function buildSpeakCommandBody(ctx: CommandBarContext, typed: string): SpeakCommandBody | null {
  const transcript = typed.trim();
  if (transcript === '' || !hasTokenCell(ctx)) return null;
  return {
    speaker_id: ctx.speakerId,
    speaker_name: ctx.speakerName,
    transcript,
    session_id: ctx.sessionId,
    campaign_id: ctx.campaignId,
    token_id: ctx.tokenId as string,
    from_x: ctx.fromX as number,
    from_y: ctx.fromY as number,
    grid_cols: ctx.gridCols,
    grid_rows: ctx.gridRows,
  };
}
