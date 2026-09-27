import { css } from 'lit';
import { layoutStyles } from './caravan/styles/layout.styles.ts';
import { cardStyles } from './caravan/styles/card.styles.ts';
import { modalStyles } from './caravan/styles/modal.styles.ts';

export { layoutStyles, cardStyles, modalStyles };

export const caravanBoardStyles = css`
  ${layoutStyles}
  ${cardStyles}
  ${modalStyles}
`;
