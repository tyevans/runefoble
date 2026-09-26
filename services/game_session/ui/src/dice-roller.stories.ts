import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dice-roller.ts';

const meta: Meta = {
  title: 'Gameplay/RunefobleDiceRoller',
  component: 'runefoble-dice-roller',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const StandardD20Roll: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-1"
        rollerId="player-valeros"
        rollerName="Valeros (Fighter)"
        formula="1d20+3"
      ></runefoble-dice-roller>
    </div>
  `,
};

export const AdvantageAttack: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-2"
        rollerId="player-merisiel"
        rollerName="Merisiel (Rogue - Sneak Attack)"
        formula="2d20kh1+5"
      ></runefoble-dice-roller>
    </div>
  `,
};

export const Fireball8d6: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-3"
        rollerId="player-ezren"
        rollerName="Ezren (Wizard - Fireball)"
        formula="8d6+4"
      ></runefoble-dice-roller>
    </div>
  `,
};

export const CriticalHit: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-4"
        rollerId="player-valeros"
        rollerName="Valeros (Critical Strike!)"
        formula="1d20+6"
        .forcedResult=${{
          formula: '1d20+6',
          count: 1,
          sides: 20,
          modifier: 6,
          rolls: [20],
          keptRolls: [20],
          total: 26,
          isCrit: true,
          isFumble: false,
        }}
      ></runefoble-dice-roller>
    </div>
  `,
};

export const CriticalFumble: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-5"
        rollerId="player-kyra"
        rollerName="Kyra (Disastrous Slip!)"
        formula="1d20+2"
        .forcedResult=${{
          formula: '1d20+2',
          count: 1,
          sides: 20,
          modifier: 2,
          rolls: [1],
          keptRolls: [1],
          total: 3,
          isCrit: false,
          isFumble: true,
        }}
      ></runefoble-dice-roller>
    </div>
  `,
};
