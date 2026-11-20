/**
 * Shapes of the DM whisper bar (TASK-0949). The field names follow The Watcher replies.
 */

export interface WhisperItem {
  whisper_id: string;
  /** `narration` for a whisper from the language model. The DM and other flows add other types. */
  whisper_type: string;
  content: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export interface PendingActionItem {
  action_id: string;
  actor_name: string;
  action_type: string;
  description: string;
  target?: string | null;
  parameters?: Record<string, unknown>;
  /** `pending`, `modified`, `approved`, `vetoed` or `expired`. */
  status?: string;
  pause_window_ms?: number;
  /** End of the pause window, in epoch seconds. */
  expires_at?: number;
}

/**
 * Detail of the `action-vetoed` event. The host posts it to `POST /api/v1/watcher/veto`, then
 * calls `markActionVetoed(actionId)` or `showActionError(message)` on the bar.
 */
export interface ActionVetoedDetail {
  actionId: string;
  reason: string;
  sessionId: string;
  campaignId: string;
}
