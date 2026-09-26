import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-character-card.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCharacterCard',
  component: 'runefoble-character-card',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ActivePlayer: Story = {
  render: () => html`
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
          description: '+1 to attack rolls and saving throws',
        },
      ]}
    ></runefoble-character-card>
  `,
};

export const MissingPlayerAiStandIn: Story = {
  render: () => html`
    <runefoble-character-card
      characterName="Kyra the Sun Maiden"
      characterClass="Cleric Lvl 4"
      .isAiStandIn=${true}
      .currentHp=${26}
      .maxHp=${32}
      .armorClass=${16}
      .initiative=${0}
      .speed=${25}
      .conditions=${[
        {
          id: 'p1',
          name: 'Drunk (Missed Session)',
          severity: 'moderate',
          source: 'session_penalty',
          description: 'The player missed session 12! Kyra consumed too much dwarven ale. Disadvantage on perception checks.',
        },
        {
          id: 'p2',
          name: 'Foolishness',
          severity: 'minor',
          source: 'session_penalty',
          description: 'AI stand-in will roleplay with reckless confidence.',
        },
      ]}
    ></runefoble-character-card>
  `,
};
