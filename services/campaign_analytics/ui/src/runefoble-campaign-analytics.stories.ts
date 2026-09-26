import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-analytics.ts';
import type {
  CampaignHeatmapResponse,
  CampaignMvpResponse,
  CampaignTimelineResponse,
} from './types.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCampaignAnalytics',
  component: 'runefoble-campaign-analytics',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

// --- Mock Datasets ---

const MOCK_HEATMAP_ACTIVE: CampaignHeatmapResponse = {
  campaign_id: 'c-sunken-temple',
  session_id: 'sess-03',
  cell_size: 5,
  metric: 'all',
  total_points: 34,
  max_density: 12,
  cells: [
    { x: 2, y: 3, density: 4, movement_count: 2, damage_total: 18, hit_count: 2, knockout_count: 0 },
    { x: 3, y: 3, density: 9, movement_count: 4, damage_total: 42, hit_count: 5, knockout_count: 0 },
    { x: 4, y: 4, density: 12, movement_count: 6, damage_total: 68, hit_count: 8, knockout_count: 1 },
    { x: 5, y: 4, density: 8, movement_count: 3, damage_total: 35, hit_count: 4, knockout_count: 0 },
    { x: 5, y: 5, density: 6, movement_count: 5, damage_total: 24, hit_count: 3, knockout_count: 0 },
    { x: 6, y: 5, density: 2, movement_count: 2, damage_total: 8, hit_count: 1, knockout_count: 0 },
  ],
  corridors: [
    { fromX: 1, fromY: 2, toX: 3, toY: 3, count: 2, tokenName: 'Valeros' },
    { fromX: 3, fromY: 3, toX: 4, toY: 4, count: 4, tokenName: 'Valeros' },
    { fromX: 2, fromY: 4, toX: 4, toY: 4, count: 3, tokenName: 'Kyra' },
  ],
  hazards: [
    { x: 4, y: 5, hazardType: 'Spike Pit', triggerCount: 2 },
  ],
  knockouts: [
    { x: 4, y: 4, characterName: 'Goblin Berserker', round: 3 },
  ],
};

const MOCK_MVP_ACTIVE: CampaignMvpResponse = {
  campaign_id: 'c-sunken-temple',
  session_id: 'sess-03',
  encounter_id: 'enc-grotto-clash',
  overall_mvp: {
    title: 'Supreme Vanguard',
    recipient_id: 'char-valeros',
    recipient_name: 'Valeros the Fighter',
    metric_name: 'Damage & Criticals',
    score: 84.5,
    description: 'Dealt 68 total damage and landed 2 lethal critical strikes in Round 3.',
  },
  awards: [
    {
      title: 'Divine Conduit',
      recipient_id: 'char-kyra',
      recipient_name: 'Kyra the Cleric',
      metric_name: 'Healing Provided',
      score: 34,
      description: 'Stabilized Ezren at 0 HP while intoxicated on Dwarven stout.',
    },
    {
      title: 'Arcane Precision',
      recipient_id: 'char-ezren',
      recipient_name: 'Ezren the Wizard',
      metric_name: 'AoE Control',
      score: 52,
      description: 'Pinned 4 goblins in Web spell.',
    },
    {
      title: 'Fumble Monarch',
      recipient_id: 'char-merisiel',
      recipient_name: 'Merisiel the Rogue',
      metric_name: 'Critical Fumbles',
      score: 3,
      description: 'Dropped rapier in subterranean sludge.',
    },
  ],
  combatants: [
    {
      combatant_id: 'char-valeros',
      combatant_name: 'Valeros',
      damage_dealt: 68,
      damage_taken: 24,
      healing_provided: 0,
      critical_hits: 2,
      fumbles: 0,
      turns_taken: 4,
      mvp_score: 84.5,
    },
    {
      combatant_id: 'char-kyra',
      combatant_name: 'Kyra',
      damage_dealt: 18,
      damage_taken: 16,
      healing_provided: 34,
      critical_hits: 1,
      fumbles: 0,
      turns_taken: 4,
      mvp_score: 72.0,
    },
    {
      combatant_id: 'char-ezren',
      combatant_name: 'Ezren',
      damage_dealt: 45,
      damage_taken: 28,
      healing_provided: 0,
      critical_hits: 0,
      fumbles: 1,
      turns_taken: 4,
      mvp_score: 52.0,
    },
    {
      combatant_id: 'char-merisiel',
      combatant_name: 'Merisiel',
      damage_dealt: 32,
      damage_taken: 12,
      healing_provided: 0,
      critical_hits: 1,
      fumbles: 3,
      turns_taken: 4,
      mvp_score: 41.0,
    },
  ],
};

const MOCK_TIMELINE_ACTIVE: CampaignTimelineResponse = {
  campaign_id: 'c-sunken-temple',
  session_id: 'sess-03',
  total_milestones: 4,
  milestones: [
    {
      id: 'm-1',
      campaign_id: 'c-sunken-temple',
      session_id: 'sess-03',
      type: 'session_start',
      title: 'Breach into the Sunken Grotto',
      description: 'The party kick down the stone sarcophagus door and enter the waterlogged vault.',
      timestamp: '19:00:15',
      metadata: { round: 1 },
    },
    {
      id: 'm-2',
      campaign_id: 'c-sunken-temple',
      session_id: 'sess-03',
      type: 'boss_encounter',
      title: 'Ambush by Skittering Broodmother',
      description: 'Massive chitinous monstrosity drops from stalactites onto the party frontline.',
      timestamp: '19:22:40',
      metadata: { round: 2 },
    },
    {
      id: 'm-3',
      campaign_id: 'c-sunken-temple',
      session_id: 'sess-03',
      type: 'character_knockout',
      title: 'Goblin Berserker Decapitated',
      description: 'Valeros cleaves through the remaining berserker at coordinates (4, 4).',
      timestamp: '19:35:10',
      metadata: { round: 3 },
    },
    {
      id: 'm-4',
      campaign_id: 'c-sunken-temple',
      session_id: 'sess-03',
      type: 'recap',
      title: 'The Watcher Narrative Summary',
      description: 'With the broodmother banished, the party salvages the glowing Sapphire of Pelor.',
      timestamp: '19:50:00',
      metadata: { round: 4, audio_url: '/audio/recaps/sess-03.mp3' },
    },
  ],
};

// --- Stories ---

export const EmptyState: Story = {
  render: () => html`
    <runefoble-campaign-analytics
      campaignId="c-fresh-journey"
    ></runefoble-campaign-analytics>
  `,
};

export const ActiveCombatTelemetry: Story = {
  render: () => html`
    <runefoble-campaign-analytics
      campaignId="c-sunken-temple"
      sessionId="sess-03"
      encounterId="enc-grotto-clash"
      .heatmapData=${MOCK_HEATMAP_ACTIVE}
      .mvpData=${MOCK_MVP_ACTIVE}
      .timelineData=${MOCK_TIMELINE_ACTIVE}
    ></runefoble-campaign-analytics>
  `,
};

export const VictoryCelebration: Story = {
  render: () => html`
    <runefoble-campaign-analytics
      campaignId="c-sunken-temple"
      sessionId="sess-final"
      .heatmapData=${{
        ...MOCK_HEATMAP_ACTIVE,
        cells: [
          ...MOCK_HEATMAP_ACTIVE.cells,
          { x: 7, y: 7, density: 15, movement_count: 8, damage_total: 120, hit_count: 10, knockout_count: 2 },
        ],
      }}
      .mvpData=${{
        ...MOCK_MVP_ACTIVE,
        overall_mvp: {
          title: 'Dragonslayer Legend',
          recipient_id: 'char-valeros',
          recipient_name: 'Valeros',
          metric_name: 'Boss Finisher',
          score: 150.0,
          description: 'Landed the decisive 74 damage critical strike against the Ancient Wyrm!',
        },
      }}
      .timelineData=${{
        ...MOCK_TIMELINE_ACTIVE,
        milestones: [
          ...MOCK_TIMELINE_ACTIVE.milestones,
          {
            id: 'm-final',
            campaign_id: 'c-sunken-temple',
            session_id: 'sess-final',
            type: 'session_end',
            title: 'Victory Banquet & Campaign Epilogue',
            description: 'The kingdom is saved, the dragon hoards distributed, and songs sung across taverns.',
            timestamp: '21:00:00',
            metadata: { round: 10 },
          },
        ],
      }}
    ></runefoble-campaign-analytics>
  `,
};

export const TotalPartyKill: Story = {
  render: () => html`
    <runefoble-campaign-analytics
      campaignId="c-tomb-of-horrors"
      sessionId="sess-tpk-09"
      .heatmapData=${{
        ...MOCK_HEATMAP_ACTIVE,
        cells: [
          { x: 5, y: 5, density: 25, movement_count: 1, damage_total: 350, hit_count: 4, knockout_count: 4 },
        ],
        knockouts: [
          { x: 5, y: 5, characterName: 'Valeros', round: 2 },
          { x: 5, y: 5, characterName: 'Kyra', round: 2 },
          { x: 5, y: 5, characterName: 'Ezren', round: 2 },
          { x: 5, y: 5, characterName: 'Merisiel', round: 2 },
        ],
      }}
      .mvpData=${{
        campaign_id: 'c-tomb-of-horrors',
        session_id: 'sess-tpk-09',
        overall_mvp: {
          title: 'Valiant Last Stand',
          recipient_id: 'char-valeros',
          recipient_name: 'Valeros',
          metric_name: 'Damage Absorbed',
          score: 95.0,
          description: 'Held the crushing sphere for two rounds before succumbing.',
        },
        awards: [
          {
            title: 'Tragic Demise',
            recipient_id: 'char-ezren',
            recipient_name: 'Ezren',
            metric_name: 'Overkill Damage',
            score: 110,
            description: 'Vaporized by Sphere of Annihilation.',
          },
        ],
        combatants: [
          { combatant_id: 'char-valeros', combatant_name: 'Valeros', damage_dealt: 12, damage_taken: 85, healing_provided: 0, critical_hits: 0, fumbles: 1, turns_taken: 2, mvp_score: 20 },
          { combatant_id: 'char-kyra', combatant_name: 'Kyra', damage_dealt: 0, damage_taken: 64, healing_provided: 22, critical_hits: 0, fumbles: 0, turns_taken: 2, mvp_score: 15 },
        ],
      }}
      .timelineData=${{
        campaign_id: 'c-tomb-of-horrors',
        session_id: 'sess-tpk-09',
        total_milestones: 2,
        milestones: [
          {
            id: 'm-tpk-1',
            campaign_id: 'c-tomb-of-horrors',
            session_id: 'sess-tpk-09',
            type: 'character_knockout',
            title: 'Total Party Annihilation',
            description: 'All 4 heroes succumb to the Devourer trap at coordinates (5, 5).',
            timestamp: '20:15:00',
            metadata: { round: 2 },
          },
          {
            id: 'm-tpk-2',
            campaign_id: 'c-tomb-of-horrors',
            session_id: 'sess-tpk-09',
            type: 'recap',
            title: 'Chronicle of the Fallen',
            description: 'The Watcher eulogizes the brave adventurers.',
            timestamp: '20:20:00',
            metadata: { round: 2, audio_url: '/audio/recaps/tpk.mp3' },
          },
        ],
      }}
    ></runefoble-campaign-analytics>
  `,
};
