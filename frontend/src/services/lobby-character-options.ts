import type { LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem } from '@runefoble/character-sheet-ui';

/** Orders the lobby character picker: the campaign's own characters first. Pure selection, no data invented. */
export function resolveLobbyAvailableCharacters(characters: CharacterItem[], campaignId?: string): LobbyCharacterOption[] {
  const sorted = campaignId ? [...characters.filter((c) => c.campaignId === campaignId), ...characters.filter((c) => !c.campaignId), ...characters.filter((c) => c.campaignId && c.campaignId !== campaignId)] : characters;
  return sorted.map((c) => ({ id: c.id, name: c.name, characterClass: c.characterClass, level: c.level, portraitUrl: c.portraitUrl }));
}
