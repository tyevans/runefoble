import type { CSSResultGroup } from 'lit';
import {
  settingsModalLayoutStyles,
  layoutStyles,
} from './styles/settings-modal-layout.styles.ts';
import {
  settingsModalTabsStyles,
  tabsStyles,
} from './styles/settings-modal-tabs.styles.ts';
import {
  settingsModalControlsStyles,
  controlsStyles,
} from './styles/settings-modal-controls.styles.ts';

export {
  settingsModalLayoutStyles,
  layoutStyles,
  settingsModalTabsStyles,
  tabsStyles,
  settingsModalControlsStyles,
  controlsStyles,
};

export const settingsModalStyles: CSSResultGroup = [
  layoutStyles,
  tabsStyles,
  controlsStyles,
];
