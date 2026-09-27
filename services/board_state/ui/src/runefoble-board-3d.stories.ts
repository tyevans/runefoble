import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './physics_3d/runefoble-tabletop-3d.ts';
import type { Miniature3DToken } from './physics_3d/miniature_mesh.ts';

const meta: Meta = {
  title: 'TTRPG/Tabletop3DPhysics',
  component: 'runefoble-tabletop-3d',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleTokens: Miniature3DToken[] = [
  { id: '1', name: 'Valeros', x: 2, y: 3, color: '#2563eb', hp: 38, maxHp: 45, isActiveTurn: true, condition: 'blessed' },
  { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: '#db2777', hp: 28, maxHp: 32, condition: 'none' },
  { id: '3', name: 'Minotaur', x: 1, y: 3, isHostile: true, color: '#dc2626', hp: 76, maxHp: 76, condition: 'none' },
  { id: '4', name: 'Goblin', x: 5, y: 1, isHostile: true, color: '#16a34a', hp: 7, maxHp: 12, condition: 'stunned' },
];

const sampleTerrain = [
  { x: 4, y: 2, elevation: 1 },
  { x: 4, y: 3, elevation: 2 },
  { x: 4, y: 4, elevation: 2 },
  { x: 5, y: 3, elevation: 3 },
];

export const TumblingDiceRoll: Story = {
  render: () => {
    const onRoll = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-tabletop-3d') as any;
      el?.rollDice({
        diceType: 'd20',
        faceValue: 20,
        settledCell: [4, 4],
        trajectory: [
          { x: 1, y: 1, z: 3.5 },
          { x: 2.5, y: 2.5, z: 2.0 },
          { x: 3.5, y: 3.2, z: 1.2 },
          { x: 4.0, y: 4.0, z: 0.1 },
        ],
      });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button style="width: fit-content; padding: 6px 12px; background: #fbbf24; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onRoll}>
          🎲 Roll 3D Tumbling d20 (Critical 20)
        </button>
        <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}></runefoble-tabletop-3d>
      </div>
    `;
  },
};

export const TokenKnockbackImpulse: Story = {
  render: () => {
    const onKnockback = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-tabletop-3d') as any;
      el?.knockbackToken({
        tokenId: '1',
        fromX: 2,
        fromY: 3,
        toX: 3,
        toY: 3,
        collided: true,
        collisionType: 'wall',
        impactEnergy: 18.5,
      });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button style="width: fit-content; padding: 6px 12px; background: #dc2626; color: white; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onKnockback}>
          💥 Minotaur Bull-Rush Knockback into Wall
        </button>
        <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}></runefoble-tabletop-3d>
      </div>
    `;
  },
};

export const ElevationStepFall: Story = {
  render: () => html`
    <runefoble-tabletop-3d
      .cols=${8}
      .rows=${8}
      .tokens=${[
        { id: '1', name: 'Valeros', x: 5, y: 3, color: '#2563eb', hp: 38, maxHp: 45, condition: 'blessed' },
        { id: '4', name: 'Goblin', x: 2, y: 2, isHostile: true, color: '#16a34a', condition: 'stunned' },
      ]}
      .terrainCells=${sampleTerrain}
    ></runefoble-tabletop-3d>
  `,
};

export const LightThemeTabletop: Story = {
  render: () => html`
    <runefoble-tabletop-3d
      .cols=${8}
      .rows=${8}
      .tokens=${sampleTokens}
      .terrainCells=${sampleTerrain}
      theme="light"
    ></runefoble-tabletop-3d>
  `,
};
