import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './physics_3d/runefoble-tabletop-3d.ts';
import type { Miniature3DToken } from './physics_3d/miniature_mesh.ts';

const meta: Meta = {
  title: 'TTRPG/MiniatureKnockback3D',
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

export const BullRushShove: Story = {
  render: () => {
    const onShove = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-tabletop-3d') as any;
      el?.knockbackToken({ tokenId: '1', fromX: 2, fromY: 3, toX: 5, toY: 3, distanceFt: 15.0, impactEnergy: 12.0 });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button style="width: fit-content; padding: 6px 12px; background: #dc2626; color: white; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onShove}>
          🐂 Minotaur Bull-Rush Shove (15ft Slide & Deceleration)
        </button>
        <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}></runefoble-tabletop-3d>
      </div>
    `;
  },
};

export const CliffDropFall: Story = {
  render: () => {
    const onDrop = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-tabletop-3d') as any;
      el?.knockbackToken({ tokenId: '1', fromX: 4, fromY: 3, toX: 2, toY: 3, collided: false, impactEnergy: 18.0 });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button style="width: fit-content; padding: 6px 12px; background: #eab308; color: #000; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onDrop}>
          ⛰️ Shove Off Ledge (Gravity Fall & Upright Recovery)
        </button>
        <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${[{ id: '1', name: 'Valeros', x: 4, y: 3, color: '#2563eb' }]} .terrainCells=${sampleTerrain}></runefoble-tabletop-3d>
      </div>
    `;
  },
};

export const WallBounceRebound: Story = {
  render: () => {
    const onWallBounce = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-tabletop-3d') as any;
      el?.knockbackToken({ tokenId: '1', fromX: 2, fromY: 3, toX: 4, toY: 3, collided: true, collisionType: 'wall', impactEnergy: 24.5 });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <button style="width: fit-content; padding: 6px 12px; background: #475569; color: white; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onWallBounce}>
          🧱 Wall Collision Rebound & Restitution
        </button>
        <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain}></runefoble-tabletop-3d>
      </div>
    `;
  },
};

export const LightThemeKnockback: Story = {
  render: () => html`
    <div style="display: flex; flex-direction: column; gap: 8px; background: #f8fafc; padding: 12px; border-radius: 8px;">
      <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} theme="light"></runefoble-tabletop-3d>
    </div>
  `,
};

export const HighContrastKnockback: Story = {
  render: () => html`
    <div style="display: flex; flex-direction: column; gap: 8px; background: #000; padding: 12px; border-radius: 8px;">
      <runefoble-tabletop-3d .cols=${8} .rows=${8} .tokens=${sampleTokens} .terrainCells=${sampleTerrain} theme="high-contrast"></runefoble-tabletop-3d>
    </div>
  `,
};
