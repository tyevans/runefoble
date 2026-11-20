/**
 * App Shell Active Character Selection (TASK-0642, TASK-0972).
 *
 * Picks the character that the session view binds to. The caller binds only the caller's own
 * character in the campaign. A seat that the caller holds wins over the caller's other characters.
 * The result is null when the caller owns no character in the campaign. No other player's
 * character is ever chosen, and no placeholder character is created (ADR-0015).
 */

import type { CharacterItem } from '@runefoble/character-sheet-ui';
import type { SessionParticipant } from '../services/owner-wire-mappers.ts';

/** The seat that the caller holds in the live session, or null. Another player's seat is never returned (TASK-0974). */
export function findCallerSeat(participants: SessionParticipant[], currentUserId: string): SessionParticipant | null {
  if (currentUserId === '') return null;
  return participants.find((p) => p.userId === currentUserId) ?? null;
}

/**
 * Returns the caller's character in the campaign, or null. `seatCharacterId` is the character the
 * caller holds a seat with. It counts only when the caller owns it.
 */
export function pickActiveCharacter(
  characters: CharacterItem[],
  campaignId: string,
  currentUserId: string,
  seatCharacterId: string | null,
): CharacterItem | null {
  const isOwnInCampaign = (c: CharacterItem) => c.campaignId === campaignId && currentUserId !== '' && c.ownerId === currentUserId;
  const seat = seatCharacterId ? characters.find((c) => c.id === seatCharacterId) : undefined;
  if (seat && isOwnInCampaign(seat)) return seat;
  return characters.find(isOwnInCampaign) ?? null;
}
