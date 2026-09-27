import { CSSResult } from 'lit';
import { compendiumBaseStyles } from './styles/compendium-base.styles.ts';
import { encounterBuilderStyles } from './styles/encounter-builder.styles.ts';
import { homebrewFormStyles } from './styles/homebrew-form.styles.ts';

export * from './styles/compendium-base.styles.ts';
export * from './styles/encounter-builder.styles.ts';
export * from './styles/homebrew-form.styles.ts';

export const compendiumStyles: CSSResult[] = [
  compendiumBaseStyles,
  encounterBuilderStyles,
  homebrewFormStyles,
];
