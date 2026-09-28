import { CSSResult } from 'lit';
import { baseStyles } from './styles/dashboard/base.styles.ts';
import { cardStyles } from './styles/dashboard/cards.styles.ts';
import { modalStyles } from './styles/dashboard/modal.styles.ts';

export const campaignDashboardStyles: CSSResult[] = [
  baseStyles,
  cardStyles,
  modalStyles,
];
