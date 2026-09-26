/**
 * Character Sheet UI Data Types & Condition Mechanics Reference.
 * Governing ADRs: ADR-0004, ADR-0013.
 */

export interface InventoryItem {
  item_id: string;
  name: string;
  quantity: number;
  weight_lbs: number;
  slot?: 'main_hand' | 'off_hand' | 'armor' | 'accessory';
}

export interface CharacterSheetCondition {
  id: string;
  name: string;
  condition?: string;
  severity?: 'minor' | 'moderate' | 'severe';
  source: 'tactical' | 'session_penalty' | 'spell' | 'environment' | string;
  description: string;
  duration_rounds?: number | null;
  mechanics?: string;
  savingThrowModifier?: string;
}

export interface EquipmentSlots {
  main_hand?: string | null;
  off_hand?: string | null;
  armor?: string | null;
  accessory?: string | null;
  [key: string]: string | null | undefined;
}

export type EncumbranceTier = 'light' | 'medium' | 'heavy' | 'overburdened';

export interface EncumbranceInfo {
  totalWeight: number;
  maxCapacity: number;
  tier: EncumbranceTier;
  percentage: number;
  lightThreshold: number;
  mediumThreshold: number;
  heavyThreshold: number;
}

export const KNOWN_CONDITION_DETAILS: Record<
  string,
  { mechanics: string; savingThrowModifier: string; icon: string; isPenalty?: boolean }
> = {
  blinded: {
    mechanics: 'Auto-fails checks requiring sight. Attack rolls against have advantage, creature attacks have disadvantage.',
    savingThrowModifier: 'Disadvantage on visual Dex saves',
    icon: '👁️',
  },
  prone: {
    mechanics: 'Must spend half movement to stand. Disadvantage on attack rolls. Melee attacks against have advantage.',
    savingThrowModifier: 'Disadvantage on Dex saves vs physical pushes',
    icon: '🔻',
  },
  stunned: {
    mechanics: 'Incapacitated, cannot move, speaks falteringly. Auto-fails Str and Dex saving throws.',
    savingThrowModifier: 'Auto-fails Str/Dex saves',
    icon: '⚡',
  },
  poisoned: {
    mechanics: 'Disadvantage on attack rolls and ability checks.',
    savingThrowModifier: 'Normal saves (unless specified by poison)',
    icon: '🧪',
  },
  frightened: {
    mechanics: 'Disadvantage on ability checks/attack rolls while source of fear is in sight. Cannot willingly move closer.',
    savingThrowModifier: 'Disadvantage on Wis saves vs fear source',
    icon: '😱',
  },
  unconscious: {
    mechanics: 'Incapacitated, drops what it is holding, falls prone. Auto-fails Str and Dex saving throws.',
    savingThrowModifier: 'Auto-fails Str/Dex saves',
    icon: '💤',
  },
  drunk: {
    mechanics: 'Runefoble Absence Penalty: Disadvantage on Dexterity and Perception checks. +2 temporary bravery on fear saves.',
    savingThrowModifier: '-2 to Dex saves, +2 to Wis saves vs fear',
    icon: '🍺',
    isPenalty: true,
  },
  foolishness: {
    mechanics: 'Runefoble Absence Penalty: Stand-in AI takes bold, impulsive risks without double-checking tactical hazards.',
    savingThrowModifier: '-2 to Insight & Arcana checks',
    icon: '🤡',
    isPenalty: true,
  },
  greed: {
    mechanics: 'Runefoble Absence Penalty: Must prioritize looting shiny objects or inspecting treasure chests mid-encounter.',
    savingThrowModifier: 'Disadvantage on saves vs illusions of wealth',
    icon: '💰',
    isPenalty: true,
  },
  cowardice: {
    mechanics: 'Runefoble Absence Penalty: Retreats or takes Dodge action whenever current HP drops below 40%.',
    savingThrowModifier: '+2 to movement fleeing from danger',
    icon: '🐔',
    isPenalty: true,
  },
};
