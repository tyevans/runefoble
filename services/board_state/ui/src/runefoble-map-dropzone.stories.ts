import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-map-dropzone.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleMapDropzone',
  component: 'runefoble-map-dropzone',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultIdle: Story = {
  render: () => html`
    <runefoble-map-dropzone
      uploadEndpoint="/api/v1/assets/upload"
      ownerId="dm-alicia"
    ></runefoble-map-dropzone>
  `,
};

export const ActiveUpload: Story = {
  render: () => html`
    <runefoble-map-dropzone
      .isUploading=${true}
      .uploadProgress=${55}
      ownerId="dm-alicia"
    ></runefoble-map-dropzone>
  `,
};
