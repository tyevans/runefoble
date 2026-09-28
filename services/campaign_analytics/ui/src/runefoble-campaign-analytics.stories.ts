import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-analytics.ts';
import {
  MOCK_HEATMAP_ACTIVE,
  MOCK_MVP_ACTIVE,
  MOCK_TIMELINE_ACTIVE,
  MOCK_TPK_HEATMAP,
  MOCK_TPK_MVP,
  MOCK_TPK_TIMELINE,
  MOCK_VICTORY_HEATMAP,
  MOCK_VICTORY_MVP,
  MOCK_VICTORY_TIMELINE,
} from './fixtures/campaign-analytics.fixtures.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCampaignAnalytics',
  component: 'runefoble-campaign-analytics',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const EmptyState: Story = {
  render: () => html`<runefoble-campaign-analytics campaignId="c-fresh-journey"></runefoble-campaign-analytics>`,
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
      .heatmapData=${MOCK_VICTORY_HEATMAP}
      .mvpData=${MOCK_VICTORY_MVP}
      .timelineData=${MOCK_VICTORY_TIMELINE}
    ></runefoble-campaign-analytics>
  `,
};

export const TotalPartyKill: Story = {
  render: () => html`
    <runefoble-campaign-analytics
      campaignId="c-tomb-of-horrors"
      sessionId="sess-tpk-09"
      .heatmapData=${MOCK_TPK_HEATMAP}
      .mvpData=${MOCK_TPK_MVP}
      .timelineData=${MOCK_TPK_TIMELINE}
    ></runefoble-campaign-analytics>
  `,
};

export const Default: Story = EmptyState;
export const HeatmapDensity: Story = ActiveCombatTelemetry;
export const CombatMVP: Story = ActiveCombatTelemetry;
export const ChronicleTimeline: Story = ActiveCombatTelemetry;
