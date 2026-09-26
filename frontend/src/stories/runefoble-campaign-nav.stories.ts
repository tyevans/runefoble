import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-campaign-nav.ts';

const meta: Meta = {
  title: 'Shell/RunefobleCampaignNav',
  component: 'runefoble-campaign-nav',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const LiveSessionConnected: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-campaign-nav
        campaignId="4"
        campaignTitle="Tomb of the Star-Eater"
        sessionId="14"
        dmName="The Watcher"
        userRole="Player"
        .socketConnected=${true}
      ></runefoble-campaign-nav>
    </div>
  `,
};

export const StandaloneSession: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-campaign-nav
        campaignId="5"
        campaignTitle="Whispering Depths"
        sessionId="22"
        dmName="The Watcher"
        userRole="Dungeon Master"
        .socketConnected=${false}
      ></runefoble-campaign-nav>
    </div>
  `,
};
