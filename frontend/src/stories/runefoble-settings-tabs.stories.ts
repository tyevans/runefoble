import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/settings/runefoble-settings-appearance.ts';
import '../components/settings/runefoble-settings-audio.ts';
import '../components/settings/runefoble-settings-dice.ts';

const meta: Meta = {
  title: 'Settings/TabPanels',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const AppearanceTabPanel: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-surface, #ffffff); max-width: 600px; border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);">
      <runefoble-settings-appearance currentTheme="bauhaus" currentColorMode="system"></runefoble-settings-appearance>
    </div>
  `,
};

export const AudioTabPanel: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-surface, #ffffff); max-width: 600px; border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);">
      <runefoble-settings-audio audioInputDevice="default" .noiseSuppression=${true}></runefoble-settings-audio>
    </div>
  `,
};

export const DiceTabPanel: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-surface, #ffffff); max-width: 600px; border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);">
      <runefoble-settings-dice .dicePhysics=${true} .diceSound=${true}></runefoble-settings-dice>
    </div>
  `,
};
