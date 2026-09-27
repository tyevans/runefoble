import { viewportStyles } from './viewport.styles.ts';
import { badgeStyles } from './badges.styles.ts';
import { audioStyles } from './audio.styles.ts';
import { whisperStyles } from './whisper.styles.ts';

export * from './viewport.styles.ts';
export * from './badges.styles.ts';
export * from './audio.styles.ts';
export * from './whisper.styles.ts';

export const mobileCompanionCombinedStyles = [
  viewportStyles,
  badgeStyles,
  audioStyles,
  whisperStyles,
];
