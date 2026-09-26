import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-board.ts';
import type { BoardToken } from './runefoble-board.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleBoard',
  component: 'runefoble-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleTokens: BoardToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb', hp: 38, maxHp: 45, visionRadius: 2 },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: '#db2777', hp: 28, maxHp: 32, visionRadius: 2 },
  { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: '#16a34a', hp: 7, maxHp: 12 },
  { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: '#dc2626', hp: 52, maxHp: 75 },
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
        { id: '5', name: 'Ezren', x: 1, y: 4, color: '#9333ea', hp: 22, maxHp: 22, visionRadius: 3 },
      ]}
      watcherStatus="Voice detected: 'Valeros charges 2 squares east!'"
    ></runefoble-board>
  `,
};

export const FogOfWarEncounter: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      .fogOfWar=${true}
      watcherStatus="Fog of War shrouds unrevealed dungeon corridors."
    ></runefoble-board>
  `,
};

export const ActiveTurn: Story = {
  render: () => html`
    <runefoble-board
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      activeTurnTokenId="1"
      watcherStatus="Active turn: Valeros (Fighter). 30 ft movement remaining."
    ></runefoble-board>
  `,
};

export const MultiplayerTokens: Story = {
  render: () => html`
    <runefoble-board
      .cols=${10}
      .rows=${10}
      .fogOfWar=${true}
      activeTurnTokenId="2"
      .tokens=${[
        { id: '1', name: 'Valeros', x: 3, y: 4, color: '#2563eb', hp: 42, maxHp: 45, visionRadius: 2 },
        { id: '2', name: 'Kyra (AI)', x: 4, y: 4, isAiControlled: true, color: '#db2777', hp: 12, maxHp: 32, visionRadius: 3 },
        { id: '3', name: 'Merisiel', x: 2, y: 5, color: '#059669', hp: 26, maxHp: 28, visionRadius: 3 },
        { id: '4', name: 'Ezren', x: 4, y: 5, color: '#7c3aed', hp: 18, maxHp: 20, visionRadius: 2 },
        { id: '5', name: 'Skeleton Archer', x: 8, y: 1, isHostile: true, color: '#dc2626', hp: 11, maxHp: 11 },
        { id: '6', name: 'Necromancer', x: 8, y: 8, isHostile: true, color: '#991b1b', hp: 35, maxHp: 40 },
      ]}
      watcherStatus="Turn 4: Kyra (AI Stand-in) is deliberating tactical healing spell."
    ></runefoble-board>
  `,
};
