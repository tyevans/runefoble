import type { ThemeMode } from './runefoble-theme-switcher.ts';

export type ColorMode = 'light' | 'dark' | 'system';

export interface ThemeOption {
  id: ThemeMode;
  name: string;
  badge: string;
  swatches: string[];
  description: string;
}

export const SETTINGS_THEME_OPTIONS: ThemeOption[] = [
  {
    id: 'bauhaus',
    name: 'Bauhaus Modernist',
    badge: '📐',
    swatches: ['#e63946', '#1d3557', '#ffb703', '#121212'],
    description: 'Primary geometric forms, solid offset shadows, and off-white canvas.',
  },
  {
    id: 'dark-fantasy',
    name: 'Dark Fantasy',
    badge: '⚔️',
    swatches: ['#0f172a', '#f59e0b', '#8b5cf6', '#06b6d4'],
    description: 'Obsidian slate atmosphere with runic purple and radiant gold.',
  },
  {
    id: 'parchment',
    name: 'Parchment',
    badge: '📜',
    swatches: ['#f4ecd8', '#9b2226', '#bb8524', '#2e1b0f'],
    description: 'Aged manuscript paper with antique crimson and brass trim.',
  },
  {
    id: 'cyber-rune',
    name: 'Cyber Rune',
    badge: '⚡',
    swatches: ['#09090b', '#06b6d4', '#ec4899', '#eab308'],
    description: 'Dark terminal synthwave with glowing cyan, pink, and yellow.',
  },
];
