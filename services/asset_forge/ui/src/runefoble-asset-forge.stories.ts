import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-asset-forge.ts';
import { withMockFetch } from './forge-story-fetch.ts';

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
      mapPreviewUrl=${sampleBattlemapSvg}
      .lastForgedMap=${{
        asset_id: 'map-forge-demo-01',
        image_url: '/api/v1/assets/map-forge-demo-01?stream=true',
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
      tokenPreviewUrl=${sampleTokenSvg}
      .lastForgedToken=${{
        asset_id: 'tok-forge-demo-01',
        image_url: '/api/v1/assets/tok-forge-demo-01?stream=true',
        token_name: 'Thorin Ironbreaker',
        token_type: 'pc',
        size_px: 256,
      }}
    ></runefoble-asset-forge>
  `,
};

const battlemapResponse = {
  asset_id: 'map-forge-demo-02',
  image_url: '/api/v1/assets/map-forge-demo-02?stream=true',
  download_url: '/api/v1/assets/map-forge-demo-02?stream=true',
  width_cells: 20,
  height_cells: 20,
  cell_size_px: 64,
  theme: 'dwarven_forge',
  wall_segments: [{ x1: 0, y1: 0, x2: 1, y2: 0 }, { x1: 1, y1: 0, x2: 1, y2: 1 }],
  hazard_cells: [{ x: 3, y: 4, hazard_type: 'lava', terrain_type: 'difficult' }],
  doors: [],
  status: 'forged',
};

const tokenResponse = {
  asset_id: 'tok-forge-demo-02',
  image_url: '/api/v1/assets/tok-forge-demo-02?stream=true',
  token_name: 'Thorin Ironbreaker',
  token_type: 'pc',
  size_px: 256,
};

const serviceUnavailable = {
  detail: 'Silo asset storage is unavailable. The asset was not stored.',
};

/** Forges a battlemap. The mocked route returns a preview on success. */
export const ForgeMapSuccess: Story = {
  decorators: [
    withMockFetch(
      { match: '/api/v1/forge/battlemap', status: 200, body: battlemapResponse },
      { match: '/api/v1/assets/map-forge-demo-02', status: 200, body: sampleBattlemapSvg, contentType: 'image/svg+xml' }
    ),
  ],
  render: () => html`
    <runefoble-asset-forge campaignId="campaign-alpha" activeTab="battlemap"></runefoble-asset-forge>
  `,
};

/** Forges a battlemap while Silo is down. The component shows the server detail. */
export const ForgeMapServiceUnavailable: Story = {
  decorators: [
    withMockFetch({ match: '/api/v1/forge/battlemap', status: 503, body: serviceUnavailable }),
  ],
  render: () => html`
    <runefoble-asset-forge campaignId="campaign-alpha" activeTab="battlemap"></runefoble-asset-forge>
  `,
};

/** Forges a token portrait. The mocked route returns a portrait on success. */
export const ForgeTokenSuccess: Story = {
  decorators: [
    withMockFetch(
      { match: '/api/v1/forge/token', status: 200, body: tokenResponse },
      { match: '/api/v1/assets/tok-forge-demo-02', status: 200, body: sampleTokenSvg, contentType: 'image/svg+xml' }
    ),
  ],
  render: () => html`
    <runefoble-asset-forge campaignId="campaign-alpha" activeTab="token"></runefoble-asset-forge>
  `,
};

/** Forges a token portrait while Silo is down. The component shows the server detail. */
export const ForgeTokenServiceUnavailable: Story = {
  decorators: [withMockFetch({ match: '/api/v1/forge/token', status: 503, body: serviceUnavailable })],
  render: () => html`
    <runefoble-asset-forge campaignId="campaign-alpha" activeTab="token"></runefoble-asset-forge>
  `,
};

/** Places a forged token on a board. Requires a session id and a forged token. */
export const PlaceTokenSuccess: Story = {
  decorators: [
    withMockFetch({
      match: '/api/v1/boards/session-demo-01/tokens',
      status: 200,
      body: { token_id: 'tok-placed-01', name: 'Thorin Ironbreaker', token_type: 'pc', x: 0, y: 0 },
    }),
  ],
  render: () => html`
    <runefoble-asset-forge
      campaignId="campaign-alpha"
      sessionId="session-demo-01"
      activeTab="token"
      tokenPreviewUrl=${sampleTokenSvg}
      .lastForgedToken=${tokenResponse}
    ></runefoble-asset-forge>
  `,
};

/** Places a token while the board service rejects the request. */
export const PlaceTokenBoardError: Story = {
  decorators: [
    withMockFetch({
      match: '/api/v1/boards/session-demo-01/tokens',
      status: 503,
      body: { detail: 'Board state is unavailable.' },
    }),
  ],
  render: () => html`
    <runefoble-asset-forge
      campaignId="campaign-alpha"
      sessionId="session-demo-01"
      activeTab="token"
      tokenPreviewUrl=${sampleTokenSvg}
      .lastForgedToken=${tokenResponse}
    ></runefoble-asset-forge>
  `,
};
