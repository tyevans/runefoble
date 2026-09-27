import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-dashboard.ts';
import type { CampaignItem } from './types.ts';

const meta: Meta = {
  title: 'GameSession/CampaignDashboard',
  component: 'runefoble-campaign-dashboard',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleCampaigns: CampaignItem[] = [
  {
    id: 'camp-1',
    title: 'Shadows of Drakkenheim',
    description:
      'A contaminated metropolis filled with eldritch horrors, rival factions, and mysterious delerium crystals.',
    setting: 'Gothic Dark Fantasy',
    system: 'SRD 5e',
    role: 'owner',
    dm_name: 'Evelyn (You)',
    player_count: 5,
    has_active_session: true,
  },
  {
    id: 'camp-2',
    title: 'Curse of Strahd: Reloaded',
    description:
      'Under raging storm clouds, the vampire Count Strahd von Zarovich stands silhouetted against the ancient walls of Castle Ravenloft.',
    setting: 'Gothic Horror',
    system: 'SRD 5e',
    role: 'player',
    dm_name: 'Marcus Vance',
    player_count: 4,
    has_active_session: false,
  },
  {
    id: 'camp-3',
    title: 'Frontier of the Sunken Spire',
    description:
      'Exploration of a sunken subterranean realm uncovered by cataclysmic earthquake in the southern wastes.',
    setting: 'Sword & Sorcery',
    system: 'Pathfinder 2e',
    role: 'dm',
    dm_name: 'Evelyn (You)',
    player_count: 6,
    has_active_session: false,
  },
  {
    id: 'camp-4',
    title: 'The Great Alchemical Hunt',
    description:
      'A light-hearted tavern crawl across the floating archipelago seeking rare reagents and legendary brews.',
    setting: 'High Fantasy Comedy',
    system: 'Daggerheart',
    role: 'player',
    dm_name: 'Sarah Chen',
    player_count: 3,
    has_active_session: true,
  },
];

export const PopulatedWithMixedRoles: Story = {
  render: () => html`
    <runefoble-campaign-dashboard
      .campaigns=${sampleCampaigns}
    ></runefoble-campaign-dashboard>
  `,
};

export const EmptyDashboard: Story = {
  render: () => html`
    <runefoble-campaign-dashboard
      .campaigns=${[]}
    ></runefoble-campaign-dashboard>
  `,
};

export const FilteredDMingOnly: Story = {
  render: () => html`
    <runefoble-campaign-dashboard
      .campaigns=${sampleCampaigns}
      activeFilter="dming"
    ></runefoble-campaign-dashboard>
  `,
};

export const FilteredPlayingOnly: Story = {
  render: () => html`
    <runefoble-campaign-dashboard
      .campaigns=${sampleCampaigns}
      activeFilter="playing"
    ></runefoble-campaign-dashboard>
  `,
};
