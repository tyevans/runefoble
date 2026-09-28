import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-combat-heatmap.ts';
import type { CampaignHeatmapResponse } from './types.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCombatHeatmap',
  component: 'runefoble-combat-heatmap',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const MOCK_HEATMAP: CampaignHeatmapResponse = {
  campaign_id: 'camp-tactical-01',
  session_id: 'sess-dungeon-01',
  cell_size: 5,
  metric: 'all',
  total_points: 42,
  max_density: 16,
  cells: [
    { x: 2, y: 3, density: 4, movement_count: 2, damage_total: 18, hit_count: 2, knockout_count: 0 },
    { x: 3, y: 3, density: 9, movement_count: 4, damage_total: 42, hit_count: 5, knockout_count: 0 },
    { x: 4, y: 4, density: 16, movement_count: 8, damage_total: 85, hit_count: 10, knockout_count: 1 },
    { x: 5, y: 4, density: 8, movement_count: 3, damage_total: 35, hit_count: 4, knockout_count: 0 },
    { x: 5, y: 5, density: 6, movement_count: 5, damage_total: 24, hit_count: 3, knockout_count: 0 },
    { x: 6, y: 5, density: 2, movement_count: 2, damage_total: 8, hit_count: 1, knockout_count: 0 },
  ],
  corridors: [
    { fromX: 1, fromY: 2, toX: 3, toY: 3, count: 3, tokenName: 'Valeros' },
    { fromX: 3, fromY: 3, toX: 4, toY: 4, count: 6, tokenName: 'Valeros' },
    { fromX: 2, fromY: 4, toX: 4, toY: 4, count: 4, tokenName: 'Kyra' },
  ],
  hazards: [
    { x: 4, y: 5, hazardType: 'Spike Pit', triggerCount: 2 },
  ],
  knockouts: [
    { x: 4, y: 4, characterName: 'Goblin Berserker', round: 3 },
  ],
};

export const DefaultAllWeights: Story = {
  render: () => html`
    <runefoble-combat-heatmap
      .heatmapData=${MOCK_HEATMAP}
      selectedMetric="all"
    ></runefoble-combat-heatmap>
  `,
};

export const DamageFilter: Story = {
  render: () => html`
    <runefoble-combat-heatmap
      .heatmapData=${MOCK_HEATMAP}
      selectedMetric="damage"
    ></runefoble-combat-heatmap>
  `,
};

export const StrikesFilter: Story = {
  render: () => html`
    <runefoble-combat-heatmap
      .heatmapData=${MOCK_HEATMAP}
      selectedMetric="hit"
    ></runefoble-combat-heatmap>
  `,
};

export const TrafficMovementFilter: Story = {
  render: () => html`
    <runefoble-combat-heatmap
      .heatmapData=${MOCK_HEATMAP}
      selectedMetric="movement"
    ></runefoble-combat-heatmap>
  `,
};

export const EmptyHeatmap: Story = {
  render: () => html`
    <runefoble-combat-heatmap></runefoble-combat-heatmap>
  `,
};
