import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-header.ts';
import type { CampaignItem } from './types.ts';

const meta: Meta = {
  title: 'GameSession/CampaignHeader',
  component: 'runefoble-campaign-header',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleCampaignFull: CampaignItem = {
  id: 'camp-drakkenheim-001',
  title: 'Shadows of Drakkenheim',
  setting: 'Gothic Fantasy',
  system: '5e',
  status: 'active',
  owner_id: 'usr-evelyn',
  dm_name: 'Evelyn',
  role: 'owner',
  player_count: 4,
  has_active_session: true,
  active_session_id: 'sess-drakken-04',
  cover_image_url: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80',
  description:
    'Contaminated gothic ruins filled with eldritch haze, mutative delirium crystals, and rival factions vying for control of the fallen throne. Survival requires cunning, diplomacy, and steel.',
};

const sampleCampaignPf2e: CampaignItem = {
  id: 'camp-frontier-002',
  title: 'Frontier Caravan Run',
  setting: 'High Fantasy Frontier',
  system: 'pf2e',
  status: 'planning',
  owner_id: 'usr-garrick',
  dm_name: 'Garrick Bronzearm',
  role: 'player',
  player_count: 5,
  has_active_session: false,
  cover_image_url: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1200&q=80',
  description:
    'Escorting supply caravans across the perilous untamed badlands of the West Marches.',
};

const sampleCampaignMinimal: CampaignItem = {
  id: 'camp-minimal-003',
  title: 'Echoes of the Void',
  system: 'call_of_cthulhu',
  owner_id: 'usr-unknown',
};

export const GameMasterView: Story = {
  render: () => html`
    <runefoble-campaign-header
      .campaign=${sampleCampaignFull}
      .canManage=${true}
      current-user-id="usr-evelyn"
      @update-campaign=${(e: CustomEvent) => console.log('update-campaign', e.detail)}
    ></runefoble-campaign-header>
  `,
};

export const PlayerView: Story = {
  render: () => html`
    <runefoble-campaign-header
      .campaign=${sampleCampaignPf2e}
      .canManage=${false}
      current-user-id="usr-marcus"
    ></runefoble-campaign-header>
  `,
};

export const MinimalMetadata: Story = {
  render: () => html`
    <runefoble-campaign-header
      .campaign=${sampleCampaignMinimal}
      .canManage=${false}
      current-user-id="usr-guest"
    ></runefoble-campaign-header>
  `,
};
