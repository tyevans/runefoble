import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-west-marches-atlas.ts';
import type {
  WestMarchesDiscovery,
  WestMarchesNotice,
  WestMarchesOutpost,
} from './runefoble-west-marches-atlas.ts';

const meta: Meta = {
  title: 'CampaignLore/RunefobleWestMarchesAtlas',
  component: 'runefoble-west-marches-atlas',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleDiscoveries: WestMarchesDiscovery[] = [
  {
    discovery_id: 'disc-1',
    name: 'Sunken Crypt of Arnor',
    discovery_type: 'dungeon',
    coordinates: { x: 280, y: 320 },
    discovered_by_campaign_id: 'camp-blue',
    discovered_by_party_name: 'Party Blue',
    description: 'Submerged ancient catacombs guarded by water elementals.',
    danger_level: 4,
    timestamp: '2026-09-24T14:30:00Z',
    notes: 'Secret entrance is hidden under the waterfall on the north face.',
    is_private: true,
  },
  {
    discovery_id: 'disc-2',
    name: 'Watcher Outpost Ruins',
    discovery_type: 'ruin',
    coordinates: { x: 520, y: 220 },
    discovered_by_campaign_id: 'camp-gold',
    discovered_by_party_name: 'Party Gold',
    description: 'Abandoned stone tower with active arcano-luminescent wards.',
    danger_level: 2,
    timestamp: '2026-09-25T11:00:00Z',
    notes: 'The celestial alignment lens is still intact on the upper floor.',
    is_private: false,
  },
  {
    discovery_id: 'disc-3',
    name: 'Whispering Mire Bog',
    discovery_type: 'hazard',
    coordinates: { x: 420, y: 550 },
    discovered_by_campaign_id: 'camp-night',
    discovered_by_party_name: 'Nightstalkers',
    description: 'Quicksand marshes infested with toxic marsh creepers.',
    danger_level: 3,
    timestamp: '2026-09-26T09:15:00Z',
    is_private: false,
  },
  {
    discovery_id: 'disc-4',
    name: 'Highport Trade Road Waypoint',
    discovery_type: 'waypoint',
    coordinates: { x: 740, y: 380 },
    discovered_by_campaign_id: 'camp-blue',
    discovered_by_party_name: 'Party Blue',
    description: 'Paved road junction linking Fort Rowan to the coastal outposts.',
    danger_level: 1,
    timestamp: '2026-09-26T16:00:00Z',
    is_private: false,
  },
];

const sampleOutposts: WestMarchesOutpost[] = [
  {
    outpost_id: 'outpost-rowan',
    name: 'Fort Rowan Frontier Settlement',
    region: 'The Shadowed Fenlands',
    level: 2,
    facilities: {
      alchemical_workshop: 2,
      watchtower: 3,
      trading_post: 2,
      arcane_forge: 1,
      herbal_rack: 2,
    },
    contributing_campaigns: ['Party Blue', 'Party Gold', 'Nightstalkers'],
    stored_resources: { gold: 350, timber: 85, stone: 40, alchemical_reagents: 18 },
    boons: [
      'Enhanced Potion Yield (+1 Potion on laboratory craft)',
      'Regional Threat Detection (Early warning for encounters)',
      'Wholesale Discounts (10% Gold discount at trading post)',
      '+2 HP Campfire Rest Recovery',
    ],
    defensive_buffer: 40,
  },
];

const sampleNotices: WestMarchesNotice[] = [
  {
    notice_id: 'notice-1',
    campaign_id: 'camp-blue',
    author_name: 'Ranger Laura',
    party_name: 'Party Blue',
    title: 'Bounty: Cull the Marsh Trolls',
    content: 'Four marsh trolls sighted harassing supply convoys east of the Old Bridge.',
    notice_type: 'bounty',
    bounty_reward: 150,
    posted_at: '2026-09-25T18:00:00Z',
  },
  {
    notice_id: 'notice-2',
    campaign_id: 'camp-gold',
    author_name: 'Paladin Bryan',
    party_name: 'Party Gold',
    title: 'Expedition Request: Crypt Excavation Assistance',
    content: 'Seeking capable spellcasters to decipher runes inside the Sunken Crypt of Arnor.',
    notice_type: 'request',
    posted_at: '2026-09-26T08:30:00Z',
  },
  {
    notice_id: 'notice-3',
    campaign_id: 'camp-night',
    author_name: 'Shadow Vex',
    party_name: 'Nightstalkers',
    title: 'Rumor: Obsidian Conduit Awakening',
    content: 'Strange violet pulses observed rising from the subterranean chasms at midnight.',
    notice_type: 'rumor',
    posted_at: '2026-09-26T12:00:00Z',
  },
];

export const DefaultFrontierView: Story = {
  render: () => html`
    <runefoble-west-marches-atlas
      sharedWorldId="world-fenlands-01"
      worldName="The Sunken Marches"
      frontierRegion="The Shadowed Fenlands"
      currentPartyId="camp-blue"
      currentPartyName="Party Blue"
      userRole="player"
      activeTab="map"
      .discoveries=${sampleDiscoveries}
      .outposts=${sampleOutposts}
      .notices=${sampleNotices}
    ></runefoble-west-marches-atlas>
  `,
};

export const CommunalStrongholdView: Story = {
  render: () => html`
    <runefoble-west-marches-atlas
      sharedWorldId="world-fenlands-01"
      worldName="The Sunken Marches"
      frontierRegion="The Shadowed Fenlands"
      currentPartyId="camp-blue"
      currentPartyName="Party Blue"
      userRole="player"
      activeTab="stronghold"
      .discoveries=${sampleDiscoveries}
      .outposts=${sampleOutposts}
      .notices=${sampleNotices}
    ></runefoble-west-marches-atlas>
  `,
};

export const TavernNoticeBoardView: Story = {
  render: () => html`
    <runefoble-west-marches-atlas
      sharedWorldId="world-fenlands-01"
      worldName="The Sunken Marches"
      frontierRegion="The Shadowed Fenlands"
      currentPartyId="camp-blue"
      currentPartyName="Party Blue"
      userRole="player"
      activeTab="tavern"
      .discoveries=${sampleDiscoveries}
      .outposts=${sampleOutposts}
      .notices=${sampleNotices}
    ></runefoble-west-marches-atlas>
  `,
};

export const RestrictedPlayerView: Story = {
  render: () => html`
    <runefoble-west-marches-atlas
      sharedWorldId="world-fenlands-01"
      worldName="The Sunken Marches"
      frontierRegion="The Shadowed Fenlands"
      currentPartyId="camp-gold"
      currentPartyName="Party Gold"
      userRole="player"
      activeTab="map"
      .discoveries=${sampleDiscoveries}
      .outposts=${sampleOutposts}
      .notices=${sampleNotices}
    ></runefoble-west-marches-atlas>
  `,
};

export const GuildOfficerAdminView: Story = {
  render: () => html`
    <runefoble-west-marches-atlas
      sharedWorldId="world-fenlands-01"
      worldName="The Sunken Marches"
      frontierRegion="The Shadowed Fenlands"
      currentPartyId="camp-officer"
      currentPartyName="Mercenary Guild HQ"
      userRole="guild_officer"
      activeTab="map"
      .discoveries=${sampleDiscoveries}
      .outposts=${sampleOutposts}
      .notices=${sampleNotices}
    ></runefoble-west-marches-atlas>
  `,
};
