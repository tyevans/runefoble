import { HttpError, request } from '@runefoble/ui-core';
import { syncCharacterResponse } from './runefoble-character-sheet.actions.ts';

/** Loads a character into the host. Returns an error message, or null on success. */
export async function loadCharacter(host: any, url: string, headers: Record<string, string>): Promise<string | null> {
  try {
    syncCharacterResponse(host, await request(url, {}, { headers }));
    return null;
  } catch (err) {
    if (err instanceof HttpError) return `Could not load the character sheet (status ${err.status}).`;
    return `Could not load the character sheet: ${err instanceof Error ? err.message : String(err)}`;
  }
}
