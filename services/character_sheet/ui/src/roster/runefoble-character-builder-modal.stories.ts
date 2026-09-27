import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-character-builder-modal.ts';

const meta: Meta = {
  title: 'CharacterSheet/CharacterBuilderModal',
  component: 'runefoble-character-builder-modal',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ModalOpen: Story = {
  render: () => html`
    <div style="height: 600px; position: relative;">
      <runefoble-character-builder-modal .open=${true}></runefoble-character-builder-modal>
    </div>
  `,
};

export const PrepopulatedModal: Story = {
  render: () => html`
    <div style="height: 600px; position: relative;">
      <runefoble-character-builder-modal
        .open=${true}
        .initialData=${{
          name: 'Ezren the Wise',
          characterClass: 'Wizard',
          subclass: 'Evocation',
          level: 3,
          maxHp: 20,
          armorClass: 13,
          speed: 30,
          portraitUrl: '/assets/portraits/wizard.svg',
          abilityScores: { str: 8, dex: 14, con: 12, int: 18, wis: 13, cha: 10 },
        }}
      ></runefoble-character-builder-modal>
    </div>
  `,
};

export const ModalClosed: Story = {
  render: () => html`
    <div style="padding: 20px;">
      <p>Builder modal is closed.</p>
      <runefoble-character-builder-modal .open=${false}></runefoble-character-builder-modal>
    </div>
  `,
};
