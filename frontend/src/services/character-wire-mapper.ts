/**
 * Maps the character wire body to the App Shell view model (TASK-0972, ADR-0015).
 *
 * The gateway sends `ownerId` (a mirror of character_sheet `owner_id`). The mapper reads either
 * name and keeps the owner on the view model. A character without an owner fails the read. No
 * mapper invents an owner, so the binding never picks a character with an unknown owner.
 */

import type { CharacterItem } from '@runefoble/character-sheet-ui';
import { dataOk, type DataResult } from './data-result.ts';
import { malformedResponse } from './required-fields.ts';

/** Maps one character. The owner is required. */
export function characterFromWire(raw: any): DataResult<CharacterItem> {
  const ownerId = raw?.ownerId ?? raw?.owner_id;
  if (typeof ownerId !== 'string') return malformedResponse('a character has no owner_id');
  return dataOk({ ...raw, ownerId });
}

/** Maps a character list. One character without an owner fails the whole read. */
export function charactersFromWire(list: unknown): DataResult<CharacterItem[]> {
  if (!Array.isArray(list)) return malformedResponse('the character list is not an array');
  const out: CharacterItem[] = [];
  for (const raw of list) {
    const mapped = characterFromWire(raw);
    if (!mapped.ok) return mapped;
    out.push(mapped.data);
  }
  return dataOk(out);
}
