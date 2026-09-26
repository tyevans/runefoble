import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-theme-switcher.ts';
import '../components/runefoble-character-card.ts';

const meta: Meta = {
  title: 'Theme/RunefobleThemeSwitcher',
  component: 'runefoble-theme-switcher',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const previewTemplate = (theme: string, title: string) => html`
  <div
    data-theme="${theme}"
    style="
      background-color: var(--rf-bg-canvas);
      color: var(--rf-text-primary);
      font-family: var(--rf-font-family);
      padding: 24px;
      border: var(--rf-border-width) solid var(--rf-border-color);
      border-radius: var(--rf-border-radius);
      box-shadow: var(--rf-shadow);
      max-width: 700px;
    "
  >
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h3 style="margin: 0; font-size: 1.25rem;">${title}</h3>
      <runefoble-theme-switcher currentTheme="${theme}"></runefoble-theme-switcher>
    </div>
    <div style="display: flex; gap: 20px; flex-wrap: wrap;">
      <runefoble-character-card
        characterName="Valeros of Korvosa"
        characterClass="Fighter Lvl 4"
        .currentHp=${38}
        .maxHp=${44}
        .armorClass=${18}
        .initiative=${2}
        .speed=${30}
        .conditions=${[
          {
            id: 'c1',
            name: 'Bless',
            source: 'spell',
            description: '+1 to attack rolls',
          },
        ]}
      ></runefoble-character-card>
      <div
        style="
          flex: 1;
          min-width: 240px;
          background: var(--rf-bg-surface);
          border: var(--rf-border-width) solid var(--rf-border-color);
          border-radius: var(--rf-border-radius);
          box-shadow: var(--rf-shadow-sm);
          padding: 16px;
        "
      >
        <h4 style="margin-top: 0;">Palette Tokens</h4>
        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.85rem;">
          <div><span style="display: inline-block; width: 14px; height: 14px; background: var(--rf-accent-primary); border: 1px solid var(--rf-border-color); vertical-align: middle; margin-right: 6px;"></span> Primary Accent</div>
          <div><span style="display: inline-block; width: 14px; height: 14px; background: var(--rf-accent-secondary); border: 1px solid var(--rf-border-color); vertical-align: middle; margin-right: 6px;"></span> Secondary Accent</div>
          <div><span style="display: inline-block; width: 14px; height: 14px; background: var(--rf-accent-tertiary); border: 1px solid var(--rf-border-color); vertical-align: middle; margin-right: 6px;"></span> Tertiary Accent</div>
        </div>
      </div>
    </div>
  </div>
`;

export const Default: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas);">
      <runefoble-theme-switcher></runefoble-theme-switcher>
    </div>
  `,
};

export const BauhausModernist: Story = {
  render: () => previewTemplate('bauhaus', 'Bauhaus Modernist (Default)'),
};

export const DarkFantasy: Story = {
  render: () => previewTemplate('dark-fantasy', 'Dark Fantasy Theme'),
};

export const Parchment: Story = {
  render: () => previewTemplate('parchment', 'Aged Parchment Theme'),
};

export const CyberRune: Story = {
  render: () => previewTemplate('cyber-rune', 'Cyber Rune Neon Theme'),
};
