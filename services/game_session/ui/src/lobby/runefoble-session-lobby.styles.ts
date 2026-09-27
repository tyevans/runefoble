import { CSSResult } from 'lit';
import { baseStyles } from './styles/base.styles.ts';
import { rosterStyles } from './styles/roster.styles.ts';
import { controlsStyles } from './styles/controls.styles.ts';

export * from './styles/base.styles.ts';
export * from './styles/roster.styles.ts';
export * from './styles/controls.styles.ts';

export const sessionLobbyStyles: CSSResult[] = [
  baseStyles,
  rosterStyles,
  controlsStyles,
];
