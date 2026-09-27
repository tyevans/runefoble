import type { CSSResultGroup } from 'lit';
import {
  characterSheetCoreStyles,
  coreStyles,
} from './runefoble-character-sheet.core.styles.ts';
import {
  characterSheetInventoryStyles,
  inventoryStyles,
} from './runefoble-character-sheet.inventory.styles.ts';
import {
  characterSheetConditionsStyles,
  conditionsStyles,
} from './runefoble-character-sheet.conditions.styles.ts';

export {
  characterSheetCoreStyles,
  coreStyles,
  characterSheetInventoryStyles,
  inventoryStyles,
  characterSheetConditionsStyles,
  conditionsStyles,
};

export const characterSheetStyles: CSSResultGroup = [
  characterSheetCoreStyles,
  characterSheetInventoryStyles,
  characterSheetConditionsStyles,
];
