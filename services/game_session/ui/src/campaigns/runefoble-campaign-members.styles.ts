import { CSSResult } from 'lit';
import { baseStyles } from './styles/base.styles.ts';
import { rosterStyles } from './styles/roster.styles.ts';
import { modalStyles } from './styles/modal.styles.ts';
import { badgeStyles } from './styles/badge.styles.ts';

export const campaignMembersStyles: CSSResult[] = [
  baseStyles,
  rosterStyles,
  modalStyles,
  badgeStyles,
];
