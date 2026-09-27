import { CSSResult } from 'lit';
import { baseStyles } from './base.styles.ts';
import { rosterStyles } from './roster.styles.ts';
import { controlsStyles } from './controls.styles.ts';

export * from './base.styles.ts';
export * from './roster.styles.ts';
export * from './controls.styles.ts';

export const sessionLobbyStyles: CSSResult[] = [
  baseStyles,
  rosterStyles,
  controlsStyles,
];
