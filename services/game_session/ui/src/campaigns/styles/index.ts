import { CSSResult } from 'lit';
import { baseStyles } from './base.styles.ts';
import { rosterStyles } from './roster.styles.ts';
import { modalStyles } from './modal.styles.ts';
import { badgeStyles } from './badge.styles.ts';
import { headerHeroStyles } from './header_hero.styles.ts';
import { headerMetaStyles } from './header_meta.styles.ts';
import { headerActionsStyles } from './header_actions.styles.ts';

export * from './base.styles.ts';
export * from './roster.styles.ts';
export * from './modal.styles.ts';
export * from './badge.styles.ts';
export * from './header_hero.styles.ts';
export * from './header_meta.styles.ts';
export * from './header_actions.styles.ts';

export const campaignMembersStyles: CSSResult[] = [
  baseStyles,
  rosterStyles,
  modalStyles,
  badgeStyles,
];

export const campaignHeaderStyles: CSSResult[] = [
  headerHeroStyles,
  headerMetaStyles,
  headerActionsStyles,
];
