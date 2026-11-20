/**
 * Session chronicle mapping (TASK-0641). Turns a gateway chronicle line into a Watcher feed row.
 * The same line comes from the chronicle read and from the live `chronicle_entry` session frame.
 */

import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';

/** One line of the session chronicle, as game_session returns it (TASK-0641). */
export interface SessionChronicleEntry {
  event_id: string;
  kind: 'stand_in_action' | 'dice_roll' | 'token_moved' | 'session_started' | 'session_ended';
  occurred_at: string;
  speaker: string;
  text: string;
  action_type?: string | null;
  penalties: string[];
}

/** Maps a chronicle line to the feed row that the Watcher feed shows. */
export function toWatcherFeedEvent(entry: SessionChronicleEntry): WatcherFeedEvent {
  const base = { id: entry.event_id, timestamp: new Date(entry.occurred_at).toLocaleTimeString(), speaker: entry.speaker, text: entry.text };
  if (entry.kind === 'stand_in_action') return { ...base, source: 'stand_in', actionType: 'speech' };
  if (entry.kind === 'dice_roll') return { ...base, source: 'player', actionType: 'dice_roll' };
  if (entry.kind === 'token_moved') return { ...base, source: 'player', actionType: 'board_move' };
  return { ...base, source: 'system' };
}
