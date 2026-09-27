/**
 * Character Roster and Party Assignment types and interfaces.
 * TASK-0211: Character Roster and Party Assignment Microfrontend
 * ADR-0004, ADR-0012, ADR-0013
 */

export interface AbilityScores {
  str: number;
  dex: number;
  con: number;
  int: number;
  wis: number;
  cha: number;
}

export interface CharacterItem {
  id: string;
  name: string;
  characterClass: string;
  subclass?: string;
  level: number;
  currentHp: number;
  maxHp: number;
  armorClass: number;
  speed?: number;
  abilityScores?: AbilityScores;
  portraitUrl?: string;
  campaignId?: string | null;
  campaignTitle?: string | null;
  ownerId?: string;
  isAiStandIn?: boolean;
}

export interface RosterCampaignOption {
  id: string;
  title: string;
}

export interface CreateCharacterPayload {
  name: string;
  characterClass: string;
  subclass?: string;
  level: number;
  maxHp: number;
  armorClass: number;
  speed: number;
  abilityScores: AbilityScores;
  portraitUrl: string;
}

export interface InspectCharacterEventDetail {
  characterId: string;
  character: CharacterItem;
}

export interface AssignCampaignEventDetail {
  characterId: string;
  campaignId: string | null;
  campaignTitle: string | null;
}

export interface DeleteCharacterEventDetail {
  characterId: string;
}

export function calcModifier(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function formatModifier(score: number): string {
  const mod = calcModifier(score);
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

export function filterCharacters(
  characters: CharacterItem[],
  query: string,
  filterMode: 'all' | 'assigned' | 'unassigned'
): CharacterItem[] {
  const q = (query || '').trim().toLowerCase();
  return characters.filter((c) => {
    if (filterMode === 'assigned' && !c.campaignId) return false;
    if (filterMode === 'unassigned' && !!c.campaignId) return false;
    if (!q) return true;
    const matchName = c.name.toLowerCase().includes(q);
    const matchClass = c.characterClass.toLowerCase().includes(q);
    const matchSubclass = (c.subclass || '').toLowerCase().includes(q);
    const matchCampaign = (c.campaignTitle || '').toLowerCase().includes(q);
    return matchName || matchClass || matchSubclass || matchCampaign;
  });
}
