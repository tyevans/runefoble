/**
 * Decides what the whisper bar shows for one whisper (TASK-0838).
 *
 * An `audience_narration` whisper the DM has not sent shows a Send action. A sent one shows a
 * sent badge. A `narration_unavailable` whisper shows a notice and never a Send action, because
 * it holds no narration text. Every other whisper shows nothing extra.
 */

export type WhisperAction = 'send' | 'sent' | 'notice' | 'none';

export interface WhisperActionInput {
  whisper_type: string;
  metadata?: Record<string, unknown>;
}

export const AUDIENCE_NARRATION = 'audience_narration';
export const NARRATION_UNAVAILABLE = 'narration_unavailable';

export function whisperAction(whisper: WhisperActionInput): WhisperAction {
  if (whisper.whisper_type === NARRATION_UNAVAILABLE) {
    return 'notice';
  }
  if (whisper.whisper_type !== AUDIENCE_NARRATION) {
    return 'none';
  }
  return whisper.metadata?.dispatched === true ? 'sent' : 'send';
}
