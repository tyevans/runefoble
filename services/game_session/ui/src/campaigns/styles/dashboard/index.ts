import { CSSResult } from 'lit';
import { baseStyles } from './base.styles.ts';
import { cardStyles } from './cards.styles.ts';
import { modalStyles } from './modal.styles.ts';

export * from './base.styles.ts';
export * from './cards.styles.ts';
export * from './modal.styles.ts';

export const campaignDashboardStyles: CSSResult[] = [
  baseStyles,
  cardStyles,
  modalStyles,
];
