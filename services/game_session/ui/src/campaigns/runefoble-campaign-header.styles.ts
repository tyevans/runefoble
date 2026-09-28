import { CSSResult } from 'lit';
import { headerHeroStyles } from './styles/header_hero.styles.ts';
import { headerMetaStyles } from './styles/header_meta.styles.ts';
import { headerActionsStyles } from './styles/header_actions.styles.ts';

export * from './styles/header_hero.styles.ts';
export * from './styles/header_meta.styles.ts';
export * from './styles/header_actions.styles.ts';

export const campaignHeaderStyles: CSSResult[] = [
  headerHeroStyles,
  headerMetaStyles,
  headerActionsStyles,
];
