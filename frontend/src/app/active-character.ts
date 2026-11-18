/**
 * App Shell Active Character Selection (TASK-0642).
 *
 * Picks the character that the session view binds to. The choice comes only from the
 * loaded roster. When the roster is empty, the result is null and the view shows an
 * empty state. No placeholder character is ever created.
 */

import type { CharacterItem } from '@runefoble/character-sheet-ui';

/** Returns the roster character assigned to the campaign, else the first roster character, else null. */
export function pickActiveCharacter(characters: CharacterItem[], campaignId: string): CharacterItem | null {
  return characters.find((c) => c.campaignId === campaignId) ?? characters[0] ?? null;
}
