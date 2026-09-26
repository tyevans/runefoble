import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-asset-forge.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleAssetForge',
  component: 'runefoble-asset-forge',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleBattlemapSvg =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#2a2830"/>
  <line x1="200" y1="0" x2="200" y2="400" stroke="#e63946" stroke-width="4"/>
  <rect x="250" y="80" width="40" height="240" fill="#e65014"/>
  <text x="200" y="200" font-family="sans-serif" font-size="16" fill="#fff" text-anchor="middle">
    DWARVEN FORGE TACTICAL MAP
  </text>
</svg>
`);

const sampleTokenSvg =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <circle cx="64" cy="64" r="60" fill="#3a405a" stroke="#e63946" stroke-width="6"/>
  <circle cx="64" cy="48" r="20" fill="#f1faee"/>
  <path d="M 34 100 Q 64 70 94 100" fill="#f1faee"/>
</svg>
`);

export const DefaultEmpty: Story = {
  render: () => html`
    <runefoble-asset-forge campaignId="campaign-alpha"></runefoble-asset-forge>
  `,
};

export const GeneratingProgress: Story = {
  render: () => html`
    <runefoble-asset-forge
      campaignId="campaign-alpha"
      .isGenerating=${true}
    ></runefoble-asset-forge>
  `,
};

export const BattlemapForgedPreview: Story = {
  render: () => html`
    <runefoble-asset-forge
      campaignId="campaign-alpha"
      activeTab="battlemap"
      .lastForgedMap=${{
        asset_id: 'map-forge-demo-01',
        image_url: sampleBattlemapSvg,
        theme: 'dwarven_forge',
        width_cells: 20,
        height_cells: 20,
        wall_count: 14,
        hazard_count: 6,
      }}
    ></runefoble-asset-forge>
  `,
};

export const TokenPortraitForged: Story = {
  render: () => html`
    <runefoble-asset-forge
      campaignId="campaign-alpha"
      activeTab="token"
      .lastForgedToken=${{
        asset_id: 'tok-forge-demo-01',
        image_url: sampleTokenSvg,
        token_name: 'Thorin Ironbreaker',
        token_type: 'pc',
        size_px: 256,
      }}
    ></runefoble-asset-forge>
  `,
};
