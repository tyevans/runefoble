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

/** The DM opens a live session that has no board yet, and sees the set-up hint. */
export const DmNoBoard: Story = {
  render: () => html`<div style="max-width: 640px; padding: 20px;"><runefoble-board-empty can-set-up-map></runefoble-board-empty></div>`,
};
