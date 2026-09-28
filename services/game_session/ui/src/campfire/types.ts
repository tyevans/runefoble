export interface CraftingOutcome {
  outcome: 'success' | 'mishap';
  message: string;
  item_name?: string;
  tags?: string[];
}

export interface CraftingBenchProps {
  availableReagents: string[];
  selectedReagents: string[];
  selectedCatalyst: string;
  calculatedRisk: number;
  lastOutcome: CraftingOutcome | null;
  onToggleReagent: (reagent: string) => void;
  onCatalystChange: (e: Event) => void;
  onCombine: () => void;
}

export interface BoonsDisplayProps {
  storytellingPrompt: string;
  restType: 'short' | 'long';
  activeBoons: string[];
  onSelectRestType: (type: 'short' | 'long') => void;
  onRest: () => void;
}

export interface StrongholdStatusProps {
  strongholdFacilities: Record<string, number>;
  onUpgrade: (facility: string) => void;
}

export const DEFAULT_PROMPT =
  'The crackling embers cast flickering warmth across tired faces. Tell a tale of the first monster that truly frightened your character.';

export const DEFAULT_REAGENTS: string[] = [
  'Glowmoss Extract',
  'Volcano Ash',
  'Star Lily',
  'Nightshade Berry',
  'Purified Quicksilver',
];

export const DEFAULT_FACILITIES: Record<string, number> = {
  watchtower: 1,
  herbal_rack: 1,
  arcane_forge: 0,
};

export const DEFAULT_BOONS: string[] = [
  'Campfire Camaraderie (+1 Morale to Initiative)',
  'Vigilant Sentry (+2 Passive Perception)',
  'Restorative Brews (+1d4 Rest Healing)',
];
