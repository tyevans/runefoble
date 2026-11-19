import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-board-empty.ts';

const meta: Meta = {
  title: 'BoardState/BoardEmpty',
  component: 'runefoble-board-empty',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

/** A player opens a live session that has no board yet. */
export const PlayerNoBoard: Story = {
  render: () => html`<div style="max-width: 640px; padding: 20px;"><runefoble-board-empty></runefoble-board-empty></div>`,
};

const SEATS = [
  { characterId: 'char-valeros', characterName: 'Valeros the Bold' },
  { characterId: 'char-sarah', characterName: 'Sarah of the Mists' },
];

/**
 * The DM opens a live session that has no board yet, and sees the hint and the "Set up battlemap"
 * control (TASK-0922). In Storybook no gateway answers, so a click shows the transport error.
 */
export const DmNoBoard: Story = {
  render: () => html`<div style="max-width: 640px; padding: 20px;"><runefoble-board-empty can-set-up-map .campaignId=${'camp-1'} .sessionId=${'sess-1'} .seats=${SEATS}></runefoble-board-empty></div>`,
};
