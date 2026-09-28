/**
 * Storybook stories for Mobile-First Touch Minigames Suite.
 * TASK-0261: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite.
 * Governed by ADR-0004, ADR-0012, PRD-0024, US-0074.
 */

import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/minigames/index.ts';

const meta: Meta = {
  title: 'Tavern/RunefobleMinigamesSuite',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const mobileWrapper = (content: unknown, theme: 'light' | 'dark' = 'light') => html`
  <div
    data-color-mode=${theme}
    style="
      padding: 16px;
      background: ${theme === 'dark' ? '#0f172a' : '#f8f9fa'};
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: flex-start;
    "
  >
    <div
      style="
        width: 375px;
        background: ${theme === 'dark' ? '#1e293b' : '#ffffff'};
        border: 2px solid ${theme === 'dark' ? '#334155' : '#0f172a'};
        box-shadow: 4px 4px 0px ${theme === 'dark' ? '#000000' : '#0f172a'};
        border-radius: 12px;
        overflow: hidden;
      "
    >
      ${content}
    </div>
  </div>
`;

export const Darts501Light: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-darts></runefoble-minigame-darts>`, 'light'),
};

export const Darts501Dark: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-darts></runefoble-minigame-darts>`, 'dark'),
};

export const LiarsDiceLight: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-liars-dice></runefoble-minigame-liars-dice>`, 'light'),
};

export const LiarsDiceDark: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-liars-dice></runefoble-minigame-liars-dice>`, 'dark'),
};

export const RouletteLight: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-roulette></runefoble-minigame-roulette>`, 'light'),
};

export const RouletteDark: Story = {
  render: () => mobileWrapper(html`<runefoble-minigame-roulette></runefoble-minigame-roulette>`, 'dark'),
};
