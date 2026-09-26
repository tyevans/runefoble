import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-map-grid-config.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleMapGridConfig',
  component: 'runefoble-map-grid-config',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleBattlemapSvg =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <rect width="800" height="600" fill="#2b2d42"/>
  <rect x="60" y="60" width="680" height="480" fill="#3a3f58" stroke="#ef233c" stroke-width="4"/>
  <circle cx="200" cy="200" r="80" fill="#4a4e69" stroke="#8d99ae" stroke-width="3"/>
  <text x="400" y="360" font-family="sans-serif" font-size="24" font-weight="bold" fill="#edf2f4" text-anchor="middle">
    DUNGEON OF THE EYELESS WYRM
  </text>
</svg>
`);

export const DefaultGrid: Story = {
  render: () => html`
    <runefoble-map-grid-config
      previewUrl="${sampleBattlemapSvg}"
      .gridCols=${10}
      .gridRows=${10}
      .shroudEnabled=${true}
      .shroudOpacity=${0.75}
    ></runefoble-map-grid-config>
  `,
};

export const DenseMaskedGrid: Story = {
  render: () => html`
    <runefoble-map-grid-config
      previewUrl="${sampleBattlemapSvg}"
      .gridCols=${20}
      .gridRows=${16}
      .shroudEnabled=${true}
      .shroudOpacity=${0.9}
    ></runefoble-map-grid-config>
  `,
};
