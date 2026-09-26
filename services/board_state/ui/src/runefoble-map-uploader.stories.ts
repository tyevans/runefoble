import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-map-uploader.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleMapUploader',
  component: 'runefoble-map-uploader',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleBattlemapSvg =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <defs>
    <pattern id="stone" width="40" height="40" patternUnits="userSpaceOnUse">
      <rect width="40" height="40" fill="#2b2d42" stroke="#1d1e2c" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="800" height="600" fill="url(#stone)"/>
  <rect x="60" y="60" width="680" height="480" fill="#3a3f58" stroke="#ef233c" stroke-width="4"/>
  <circle cx="200" cy="200" r="80" fill="#4a4e69" stroke="#8d99ae" stroke-width="3"/>
  <rect x="420" y="140" width="220" height="160" fill="#2b2d42" stroke="#d90429" stroke-width="2"/>
  <text x="400" y="360" font-family="sans-serif" font-size="24" font-weight="bold" fill="#edf2f4" text-anchor="middle">
    DUNGEON OF THE EYELESS WYRM
  </text>
  <text x="400" y="400" font-family="sans-serif" font-size="14" fill="#8d99ae" text-anchor="middle">
    Chamber 4 • Altar of Shrouds
  </text>
</svg>
`);

export const EmptyDropzone: Story = {
  render: () => html`
    <runefoble-map-uploader
      uploadEndpoint="/api/v1/assets/upload"
      ownerId="dm-alicia"
    ></runefoble-map-uploader>
  `,
};

export const UploadingProgress: Story = {
  render: () => html`
    <runefoble-map-uploader
      .isUploading=${true}
      .uploadProgress=${68}
      ownerId="dm-alicia"
    ></runefoble-map-uploader>
  `,
};

export const AlignedMapPreview: Story = {
  render: () => html`
    <runefoble-map-uploader
      previewUrl="${sampleBattlemapSvg}"
      assetId="asset-battlemap-dungeon-01"
      .gridCols=${12}
      .gridRows=${10}
      .shroudEnabled=${true}
      .shroudOpacity=${0.5}
      ownerId="dm-alicia"
    ></runefoble-map-uploader>
  `,
};

export const FogOfWarMasked: Story = {
  render: () => html`
    <runefoble-map-uploader
      previewUrl="${sampleBattlemapSvg}"
      assetId="asset-battlemap-dungeon-02"
      .gridCols=${16}
      .gridRows=${12}
      .shroudEnabled=${true}
      .shroudOpacity=${0.9}
      ownerId="dm-alicia"
    ></runefoble-map-uploader>
  `,
};
