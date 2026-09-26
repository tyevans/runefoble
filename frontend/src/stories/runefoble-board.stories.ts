import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../components/runefoble-board.ts';
import type { BoardToken } from '../components/runefoble-board.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleBoard',
  component: 'runefoble-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleTokens: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb' },
  { id: '2', name: 'Kyra (AI Stand-in)', x: 3, y: 3, isAiControlled: true, color: '#db2777' },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, color: '#16a34a' },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, color: '#dc2626' },
];

export const Default: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      watcherStatus="Tracking 4 active tokens. Awaiting DM narration."
    ></runefoble-board>
  `,
};

export const ActiveEncounter: Story = {
  render: () => html`
    <runefoble-board
      .cols=${10}
      .rows=${8}
      .tokens=${[
        ...sampleTokens,
        { id: '5', name: 'Ezren', x: 1, y: 4, color: '#9333ea' },
      ]}
      watcherStatus="Voice detected: 'Valeros charges 2 squares east!'"
    ></runefoble-board>
  `,
};
