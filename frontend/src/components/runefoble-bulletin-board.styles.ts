import type { CSSResultGroup } from 'lit';
import { bulletinBoardCardStyles } from '../styles/bulletin-board-card.styles.ts';
import { bulletinBoardDialogStyles } from '../styles/bulletin-board-dialog.styles.ts';
import { bulletinBoardLayoutStyles } from '../styles/bulletin-board-layout.styles.ts';

export {
  bulletinBoardLayoutStyles,
  bulletinBoardCardStyles,
  bulletinBoardDialogStyles,
};

export const bulletinBoardStyles: CSSResultGroup = [
  bulletinBoardLayoutStyles,
  bulletinBoardCardStyles,
  bulletinBoardDialogStyles,
];
