import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-header.ts';

const meta: Meta = {
  title: 'Shell/RunefobleHeader',
  component: 'runefoble-header',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultPartyMode: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-header
        viewMode="party"
        campaignId="4"
        sessionId="14"
        dmName="The Watcher"
        userRole="Player"
        .socketConnected=${true}
      ></runefoble-header>
    </div>
  `,
};

export const SpectatorMode: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-header
        viewMode="spectator"
        campaignId="4"
        sessionId="14"
        dmName="The Watcher"
        userRole="Spectator"
        .socketConnected=${true}
      ></runefoble-header>
    </div>
  `,
};

export const DisconnectedStandalone: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-header
        viewMode="party"
        campaignId="4"
        sessionId="14"
        dmName="The Watcher"
        userRole="Dungeon Master"
        .socketConnected=${false}
      ></runefoble-header>
    </div>
  `,
};
