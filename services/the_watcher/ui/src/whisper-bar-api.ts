/**
 * Public-route client of the DM whisper bar (TASK-0949).
 *
 * Each function calls one gateway route of The Watcher. A failure rejects with the transport
 * error. No function returns substitute whispers or actions (ADR-0015).
 */

import { postJson, request, type RequestOptions } from '@runefoble/ui-core';
import type { PendingActionItem, WhisperItem } from './whisper-bar-types.ts';

/** The session that the bar serves. */
export interface WhisperScope {
  sessionId: string;
  campaignId: string;
}

/** The reply of `GET /api/v1/watcher/whispers`. */
export interface WhisperListReply {
  whispers: WhisperItem[];
  total: number;
  /** The engine of the narration port. `none` means that no language model is configured. */
  narration_engine: string;
}

/** The narration engine value when no language model is configured. */
export const NO_NARRATION_ENGINE = 'none';

function scopeQuery(scope: WhisperScope): string {
  return new URLSearchParams({ session_id: scope.sessionId, campaign_id: scope.campaignId }).toString();
}

/** Reads the DM whispers of the session and the narration engine name. */
export function fetchWhispers(scope: WhisperScope, opts: RequestOptions): Promise<WhisperListReply> {
  return request<WhisperListReply>(`/api/v1/watcher/whispers?${scopeQuery(scope)}`, {}, opts);
}

/** Reads every action of the session with its status. */
export function fetchPendingActions(scope: WhisperScope, opts: RequestOptions): Promise<PendingActionItem[]> {
  return request<PendingActionItem[]>(`/api/v1/watcher/actions/pending?${scopeQuery(scope)}`, {}, opts);
}

/** Asks the narration port for whispers. The Watcher records each whisper that it returns. */
export function generateWhispers(scope: WhisperScope, opts: RequestOptions): Promise<WhisperItem[]> {
  return postJson<WhisperItem[]>(
    '/api/v1/watcher/whispers/generate',
    { session_id: scope.sessionId, campaign_id: scope.campaignId },
    opts,
  );
}

/** The first action that still waits for the DM, or null. */
export function openAction(actions: PendingActionItem[]): PendingActionItem | null {
  return actions.find((a) => a.status === 'pending' || a.status === 'modified') ?? null;
}
