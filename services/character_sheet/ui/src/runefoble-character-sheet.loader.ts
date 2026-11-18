import { syncCharacterResponse } from './runefoble-character-sheet.actions.ts';

/** Loads a character into the host. Returns an error message, or null on success. */
export async function loadCharacter(host: any, url: string, headers: Record<string, string>): Promise<string | null> {
  try {
    const res = await fetch(url, { headers });
    if (!res.ok) return `Could not load the character sheet (status ${res.status}).`;
    syncCharacterResponse(host, await res.json());
    return null;
  } catch (err) {
    return `Could not load the character sheet: ${err instanceof Error ? err.message : String(err)}`;
  }
}
