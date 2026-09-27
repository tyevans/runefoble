import { CSSResult } from 'lit';
import { baseStyles } from './base.styles.ts';
import { rosterStyles } from './roster.styles.ts';
import { modalStyles } from './modal.styles.ts';
import { badgeStyles } from './badge.styles.ts';

export * from './base.styles.ts';
export * from './roster.styles.ts';
export * from './modal.styles.ts';
export * from './badge.styles.ts';

export const campaignMembersStyles: CSSResult[] = [
  baseStyles,
  rosterStyles,
  modalStyles,
  badgeStyles,
];
