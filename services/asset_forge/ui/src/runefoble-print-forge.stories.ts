import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-print-forge.ts';
import { withMockFetch } from './forge-story-fetch.ts';

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

const serviceUnavailable = {
  detail: 'Silo asset storage is unavailable. The asset was not stored.',
};

/** Exports the tiled PDF. The mocked route returns a download link on success. */
export const TiledMapExportSuccess: Story = {
  decorators: [
    withMockFetch({
      match: '/api/v1/forge/print-pdf',
      status: 200,
      body: {
        asset_id: 'print-pdf-demo-01',
        download_url: 'data:application/pdf;base64,JVBERi0=',
        total_pages: 4,
        page_size: 'letter',
      },
    }),
  ],
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="tiled-map"></runefoble-print-forge>
  `,
};

/** Exports the tiled PDF while Silo is down. The component shows the server detail. */
export const TiledMapExportServiceUnavailable: Story = {
  decorators: [withMockFetch({ match: '/api/v1/forge/print-pdf', status: 503, body: serviceUnavailable })],
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="tiled-map"></runefoble-print-forge>
  `,
};

/** Exports papercraft standees. The mocked route returns a download link on success. */
export const StandeesExportSuccess: Story = {
  decorators: [
    withMockFetch({
      match: '/api/v1/forge/standees',
      status: 200,
      body: {
        asset_id: 'standees-demo-01',
        download_url: 'data:application/pdf;base64,JVBERi0=',
        standee_count: 1,
        pages: 1,
      },
    }),
  ],
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="standees"></runefoble-print-forge>
  `,
};

/** Exports papercraft standees while Silo is down. */
export const StandeesExportServiceUnavailable: Story = {
  decorators: [withMockFetch({ match: '/api/v1/forge/standees', status: 503, body: serviceUnavailable })],
  render: () => html`
    <runefoble-print-forge campaignId="campaign-demo-01" activeTab="standees"></runefoble-print-forge>
  `,
};
