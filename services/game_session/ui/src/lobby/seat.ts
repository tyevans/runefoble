/**
 * Lobby seat offer (TASK-0889).
 *
 * The offer reads the capability flags of the server reply, never a role label (ADR-0001,
 * Hard Invariant 1). The person who runs the session does not take a seat, so the readiness
 * summary never counts them.
 */

import type { LobbyParticipant } from './types.ts';

export interface SeatOfferInput {
  /** The caller holds `campaign.play` (server reply). */
  canPlay: boolean;
  /** The caller holds `campaign.run_session` (server reply). */
  canRunSession: boolean;
  currentUserId: string;
  participants: LobbyParticipant[];
}

/** True when the lobby offers the caller a seat. */
export function canTakeSeat(input: SeatOfferInput): boolean {
  if (!input.canPlay || input.canRunSession || !input.currentUserId) return false;
  return !input.participants.some((p) => p.userId === input.currentUserId);
}
