import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-faction-radar.ts';
import type { FactionData, WorldTickData } from './runefoble-faction-radar.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleFactionRadar',
  component: 'runefoble-faction-radar',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleFactions: FactionData[] = [
  {
    faction_id: 'faction-ironfang',
    name: 'Ironfang Syndicate',
    influence: 75,
    resources: 60,
    disposition: 'hostile',
    active_goal: 'Smuggle Arcane Weapons into Oakhaven',
    goal_progress: 85,
    goal_target: 100,
    rival_faction_ids: ['faction-silver-flame'],
    territory: 'Oakhaven Docks',
  },
  {
    faction_id: 'faction-arcane-order',
    name: 'Arcane Order',
    influence: 65,
    resources: 80,
    disposition: 'neutral',
    active_goal: 'Infiltrate High Spire Reliquary',
    goal_progress: 40,
    goal_target: 100,
    rival_faction_ids: [],
    territory: 'High Spire Towers',
  },
  {
    faction_id: 'faction-silver-flame',
    name: 'Silver Flame Knights',
    influence: 55,
    resources: 50,
    disposition: 'friendly',
    active_goal: 'Establish Guard Sentry Posts',
    goal_progress: 60,
    goal_target: 100,
    rival_faction_ids: ['faction-ironfang'],
    territory: 'Upper Citadel',
  },
  {
    faction_id: 'faction-shadow-cabal',
    name: 'Shadow Cabal',
    influence: 40,
    resources: 35,
    disposition: 'unfriendly',
    active_goal: 'Corrupt the Whispering Aqueduct',
    goal_progress: 25,
    goal_target: 100,
    rival_faction_ids: [],
    territory: 'Sunken Catacombs',
  },
];

const sampleBulletin: WorldTickData = {
  campaign_id: 'camp-101',
  tick_number: 3,
  intelligence_bulletin: `# 📜 THE WATCHER INTELLIGENCE BULLETIN: WORLD TICK #3
**Campaign**: \`camp-101\` | **Regional Stability**: 52/100

## ⚔️ Geopolitical & Territorial Shifts
- **[Oakhaven Docks] TRADE_SHORTAGE**: Ironfang Syndicate flooded Oakhaven Docks with black-market contraband, triggering trade shortages.

## 🏛️ Faction Agenda Progress
- **Ironfang Syndicate** (Influence: 75, Resources: 60)
  - *Active Agenda*: Smuggle Arcane Weapons into Oakhaven
  - *Progress*: 85/100%
- **Arcane Order** (Influence: 65, Resources: 80)
  - *Active Agenda*: Infiltrate High Spire Reliquary
  - *Progress*: 40/100%

## 🍻 Evolving Tavern Rumors (Player Feed Hooks)
- "Overheard at dockside tavern: 'Armed crates bearing skull crests were unloaded at the fourth pier.'"
- "High Spire guards doubled sentries after an arcane glyph was scorched into the library door."

## 👁️ The Watcher's Tactical Advisory
- Board State: Increase sentry tokens on eastern dock battlemaps.
- Merchant Cues: Increase price of martial weapons by 25%.`,
  factions: sampleFactions,
  shifts: [
    {
      faction_id: 'faction-ironfang',
      faction_name: 'Ironfang Syndicate',
      territory: 'Oakhaven Docks',
      shift_type: 'trade_shortage',
      description: 'Smuggled enchanted arms flooded the black market, drying up legitimate forge supplies.',
      severity: 'moderate',
      ripple_effects: [
        'Forge weapon prices increased by 25%',
        'Port guards on heightened alert',
        'Contraband patrols initiated',
      ],
    },
  ],
  tavern_rumors: [
    'Overheard at dockside tavern: "Armed crates bearing skull crests were unloaded at the fourth pier."',
    'High Spire guards doubled sentries after an arcane glyph was scorched into the library door.',
    'Whispers claim the Silver Flame knights refused bribes from the western merchant guild.',
  ],
  timestamp: '2026-09-26T18:00:00Z',
};

export const Default: Story = {
  render: () => html`
    <runefoble-faction-radar
      campaignId="camp-101"
      .factions=${sampleFactions}
      .bulletin=${sampleBulletin}
      .isDm=${false}
      selectedFactionId="faction-ironfang"
    ></runefoble-faction-radar>
  `,
};

export const DMPrivateBriefing: Story = {
  render: () => html`
    <runefoble-faction-radar
      campaignId="camp-101"
      .factions=${sampleFactions}
      .bulletin=${sampleBulletin}
      .isDm=${true}
      .isDrawerOpen=${true}
      selectedFactionId="faction-ironfang"
    ></runefoble-faction-radar>
  `,
};

export const PlayerPublicView: Story = {
  render: () => html`
    <runefoble-faction-radar
      campaignId="camp-101"
      .factions=${sampleFactions}
      .bulletin=${sampleBulletin}
      .isDm=${false}
      .isDrawerOpen=${true}
      selectedFactionId="faction-silver-flame"
    ></runefoble-faction-radar>
  `,
};

export const HighTensionWar: Story = {
  render: () => {
    const warFactions: FactionData[] = [
      ...sampleFactions,
      {
        faction_id: 'faction-blood-vanguard',
        name: 'Blood Vanguard',
        influence: 90,
        resources: 85,
        disposition: 'hostile',
        active_goal: 'Besiege Sunken Bastion',
        goal_progress: 95,
        goal_target: 100,
        territory: 'Outer Ramparts',
      },
    ];
    return html`
      <runefoble-faction-radar
        campaignId="camp-war-01"
        .factions=${warFactions}
        .bulletin=${{
          ...sampleBulletin,
          tick_number: 7,
          shifts: [
            ...sampleBulletin.shifts!,
            {
              faction_id: 'faction-blood-vanguard',
              faction_name: 'Blood Vanguard',
              territory: 'Outer Ramparts',
              shift_type: 'martial_law',
              description: 'Martial law declared across Outer Ramparts. Barricades constructed overnight.',
              severity: 'critical',
              ripple_effects: [
                'Curfew enforced after twilight',
                'Siege weapons visible on skyline',
              ],
            },
          ],
        }}
        .isDm=${true}
        selectedFactionId="faction-blood-vanguard"
      ></runefoble-faction-radar>
    `;
  },
};

export const EmptyState: Story = {
  render: () => html`
    <runefoble-faction-radar
      campaignId="camp-new"
      .factions=${[]}
      .bulletin=${null}
      .isDm=${true}
    ></runefoble-faction-radar>
  `,
};
