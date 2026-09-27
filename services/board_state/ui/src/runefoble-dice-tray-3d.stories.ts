import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dice-tray-3d.ts';
import type { RunefobleDiceTray3D } from './runefoble-dice-tray-3d.ts';

const meta: Meta = {
  title: 'TTRPG/DiceTray3D',
  component: 'runefoble-dice-tray-3d',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const CriticalHitD20: Story = {
  render: () => {
    const onRoll = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-dice-tray-3d') as RunefobleDiceTray3D;
      el?.roll('d20', 20, { velocity: { x: 6.2, y: 5.1, z: 2.2 } });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px; max-width: 520px;">
        <button style="width: fit-content; padding: 6px 14px; background: #fbbf24; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onRoll}>
          🎲 Roll d20 (Critical 20)
        </button>
        <runefoble-dice-tray-3d .width=${500} .height=${300}></runefoble-dice-tray-3d>
      </div>
    `;
  },
};

export const MultiDiceThrow: Story = {
  render: () => {
    const onRollAll = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-dice-tray-3d') as RunefobleDiceTray3D;
      el?.clear();
      el?.rollMultiple([
        { diceType: 'd4', targetFaceValue: 4 },
        { diceType: 'd6', targetFaceValue: 6 },
        { diceType: 'd8', targetFaceValue: 8 },
        { diceType: 'd10', targetFaceValue: 10 },
        { diceType: 'd12', targetFaceValue: 12 },
        { diceType: 'd20', targetFaceValue: 20 },
      ]);
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px; max-width: 520px;">
        <button style="width: fit-content; padding: 6px 14px; background: #3b82f6; color: white; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onRollAll}>
          🎲 Roll Full Polyhedral Set (d4 - d20)
        </button>
        <runefoble-dice-tray-3d .width=${500} .height=${300}></runefoble-dice-tray-3d>
      </div>
    `;
  },
};

export const BoundaryWallBounces: Story = {
  render: () => {
    const onBounceRoll = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-dice-tray-3d') as RunefobleDiceTray3D;
      el?.roll('d20', 18, { velocity: { x: 8.5, y: 7.2, z: 2.5 } });
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px; max-width: 520px;">
        <button style="width: fit-content; padding: 6px 14px; background: #ef4444; color: white; border: 2px solid #000; font-weight: 800; cursor: pointer;" @click=${onBounceRoll}>
          💥 High-Velocity Ricochet Throw
        </button>
        <runefoble-dice-tray-3d .width=${500} .height=${300}></runefoble-dice-tray-3d>
      </div>
    `;
  },
};

export const LightThemeTray: Story = {
  render: () => {
    const onRoll = (e: Event) => {
      const el = (e.target as HTMLElement).parentElement?.querySelector('runefoble-dice-tray-3d') as RunefobleDiceTray3D;
      el?.roll('d12', 12);
    };
    return html`
      <div style="display: flex; flex-direction: column; gap: 8px; max-width: 520px; background: #f8fafc; padding: 12px; border-radius: 8px;">
        <button style="width: fit-content; padding: 6px 14px; background: #f97316; color: white; border: 2px solid #0f172a; font-weight: 800; cursor: pointer;" @click=${onRoll}>
          🎲 Roll d12 (Light Theme)
        </button>
        <runefoble-dice-tray-3d theme="light" .width=${500} .height=${300}></runefoble-dice-tray-3d>
      </div>
    `;
  },
};

export const HighContrastTray: Story = {
  render: () => html`
    <div style="display: flex; flex-direction: column; gap: 8px; max-width: 520px; background: #000; padding: 12px; border-radius: 8px;">
      <runefoble-dice-tray-3d theme="high-contrast" .width=${500} .height=${300}></runefoble-dice-tray-3d>
    </div>
  `,
};
