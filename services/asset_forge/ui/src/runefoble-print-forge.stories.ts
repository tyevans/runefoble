import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-print-forge.ts';

const meta: Meta = {
  title: 'TTRPG/RunefoblePrintForge',
  component: 'runefoble-print-forge',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultTiledMap: Story = {
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="tiled-map"></runefoble-print-forge>
  `,
};

export const PapercraftStandees: Story = {
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="standees"></runefoble-print-forge>
  `,
};

export const StlTokenRing: Story = {
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="stl-tokens"></runefoble-print-forge>
  `,
};

export const ExportInProgress: Story = {
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" .isExporting=${true}></runefoble-print-forge>
  `,
};
