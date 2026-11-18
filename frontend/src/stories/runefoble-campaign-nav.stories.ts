import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-campaign-nav.ts';

const STORY_CAMPAIGNS = [
  { id: '4', title: 'Tomb of the Star-Eater' },
  { id: '5', title: 'Whispering Depths' },
];

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
        sessionTitle="Session #14"
        .availableCampaigns=${STORY_CAMPAIGNS}
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
        sessionTitle="Session #22"
        .availableCampaigns=${STORY_CAMPAIGNS}
        dmName="The Watcher"
        userRole="Dungeon Master"
        .socketConnected=${false}
      ></runefoble-campaign-nav>
    </div>
  `,
};
