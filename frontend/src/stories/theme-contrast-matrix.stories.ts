import type { Meta, StoryObj } from '@storybook/web-components-vite';
import { html } from 'lit';
import '@runefoble/character-sheet-ui';
import '@runefoble/the-watcher-ui';
import '@runefoble/game-session-ui';
import '../styles/themes.css';

const meta: Meta = {
  title: 'Design System/ContrastMatrix',
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj;

const sampleEvents = [
  {
    id: '1',
    timestamp: '12:00:01',
    source: 'watcher_dm' as const,
    speaker: 'The Watcher',
    text: 'A shadowy goblin darts between the sarcophagi.',
    actionType: 'dm_ruling' as const,
  },
  {
    id: '2',
    timestamp: '12:00:15',
    source: 'player' as const,
    speaker: 'Valeros',
    text: '"Hold the line! I ready my shield."',
    actionType: 'speech' as const,
  },
];

const renderSideBySide = (theme: string) => html`
  <div style="font-family: var(--rf-font-family, sans-serif);">
    <h2 style="margin-top: 0; text-transform: uppercase; font-size: 1.2rem;">
      Theme: ${theme} (Light Mode vs Dark Mode)
    </h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start;">
      <!-- Light Mode Container -->
      <div
        data-theme="${theme}"
        data-color-mode="light"
        style="background: var(--rf-bg-canvas); color: var(--rf-text-primary); padding: 20px; border: var(--rf-border-width, 2px) solid var(--rf-border-color); box-shadow: var(--rf-shadow); box-sizing: border-box;"
      >
        <h3 style="margin-top: 0; font-size: 1rem; border-bottom: 2px solid var(--rf-border-color); padding-bottom: 6px;">
          ☀️ Light Mode
        </h3>
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <runefoble-character-card
            characterName="Valeros the Bold"
            characterClass="Fighter Lvl 4"
            .currentHp=${34}
            .maxHp=${42}
            .armorClass=${18}
          ></runefoble-character-card>

          <runefoble-watcher-feed .events=${sampleEvents}></runefoble-watcher-feed>

          <runefoble-dice-roller
            sessionId="matrix-light"
            rollerName="Valeros"
            formula="1d20+5"
          ></runefoble-dice-roller>
        </div>
      </div>

      <!-- Dark Mode Container -->
      <div
        data-theme="${theme}"
        data-color-mode="dark"
        style="background: var(--rf-bg-canvas); color: var(--rf-text-primary); padding: 20px; border: var(--rf-border-width, 2px) solid var(--rf-border-color); box-shadow: var(--rf-shadow); box-sizing: border-box;"
      >
        <h3 style="margin-top: 0; font-size: 1rem; border-bottom: 2px solid var(--rf-border-color); padding-bottom: 6px;">
          🌙 Dark Mode
        </h3>
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <runefoble-character-card
            characterName="Valeros the Bold"
            characterClass="Fighter Lvl 4"
            .currentHp=${34}
            .maxHp=${42}
            .armorClass=${18}
          ></runefoble-character-card>

          <runefoble-watcher-feed .events=${sampleEvents}></runefoble-watcher-feed>

          <runefoble-dice-roller
            sessionId="matrix-dark"
            rollerName="Valeros"
            formula="1d20+5"
          ></runefoble-dice-roller>
        </div>
      </div>
    </div>
  </div>
`;

export const BauhausComparison: Story = {
  render: () => renderSideBySide('bauhaus'),
};

export const DarkFantasyComparison: Story = {
  render: () => renderSideBySide('dark-fantasy'),
};

export const ParchmentComparison: Story = {
  render: () => renderSideBySide('parchment'),
};

export const CyberRuneComparison: Story = {
  render: () => renderSideBySide('cyber-rune'),
};
