import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-dice-roller.ts';

/**
 * The roller sends every roll to the owner. A story has no owner, so the bound story shows the
 * controls only. The failed-roll story points at an unreachable address: press ROLL to see the
 * failure text. The unbound story shows that no roll is offered.
 */
const meta: Meta = {
  title: 'Gameplay/RunefobleDiceRoller',
  component: 'runefoble-dice-roller',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const BoundCharacter: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-1"
        rollerName="Valeros (Fighter)"
        formula="1d20+3"
      ></runefoble-dice-roller>
    </div>
  `,
};

export const NoCharacterBound: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller sessionId="sess-test-2"></runefoble-dice-roller>
    </div>
  `,
};

export const FailedRoll: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-dice-roller
        sessionId="sess-test-3"
        rollerName="Merisiel (Rogue)"
        apiBaseUrl="http://127.0.0.1:9"
        formula="2d20kh1+5"
      ></runefoble-dice-roller>
    </div>
  `,
};
