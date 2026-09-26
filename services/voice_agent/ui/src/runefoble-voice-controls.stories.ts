import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-voice-controls.ts';

const meta: Meta = {
  title: 'Voice/RunefobleVoiceControls',
  component: 'runefoble-voice-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultMuted: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls></runefoble-voice-controls>
    </div>
  `,
};

export const StreamingActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls .isListening=${true}></runefoble-voice-controls>
    </div>
  `,
};

export const CustomChannelDisabled: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls
        channelName="Spectator Whispers"
        .disabled=${true}
      ></runefoble-voice-controls>
    </div>
  `,
};
