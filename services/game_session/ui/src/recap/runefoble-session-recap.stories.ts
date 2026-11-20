import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-session-recap.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleSessionRecap',
  component: 'runefoble-session-recap',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const EmptyRecap: Story = {
  render: () => html`<runefoble-session-recap session-title="Crypt of the Restless Kings" .entries=${[]}></runefoble-session-recap>`,
};

export const DiceAndMoves: Story = {
  render: () => html`
    <runefoble-session-recap
      session-title="Crypt of the Restless Kings"
      .entries=${[
        { id: 'e1', speaker: 'system', text: 'Session started.', source: 'system' },
        { id: 'e2', speaker: 'Valeros the Bold', text: '1d20 = 14', source: 'player', actionType: 'dice_roll' },
        { id: 'e3', speaker: 'Valeros the Bold', text: 'Valeros moved to 3,4', source: 'player', actionType: 'board_move' },
        { id: 'e4', speaker: 'Sarah of the Mists', text: '2d6 = 9', source: 'player', actionType: 'dice_roll' },
        { id: 'e5', speaker: 'system', text: 'Session ended.', source: 'system' },
      ]}
    ></runefoble-session-recap>
  `,
};

export const StandInAction: Story = {
  render: () => html`
    <runefoble-session-recap
      session-title="Crypt of the Restless Kings"
      .entries=${[
        { id: 's1', speaker: 'Kyra', text: 'Hold the line!', source: 'stand_in', actionType: 'speech' },
        { id: 's2', speaker: 'system', text: 'Session ended.', source: 'system' },
      ]}
    ></runefoble-session-recap>
  `,
};
