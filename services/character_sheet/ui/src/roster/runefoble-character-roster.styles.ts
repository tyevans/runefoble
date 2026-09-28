import type { CSSResultGroup } from 'lit';
import { rosterLayoutStyles } from './styles/roster_layout.styles.ts';
import { characterCardStyles } from './styles/character_card.styles.ts';
import { assignmentDialogStyles } from './styles/assignment_dialog.styles.ts';

export {
  rosterLayoutStyles,
  characterCardStyles,
  assignmentDialogStyles,
};

export const characterRosterStyles: CSSResultGroup = [
  rosterLayoutStyles,
  characterCardStyles,
  assignmentDialogStyles,
];
