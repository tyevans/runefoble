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

export const Inactive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls
        .isListening=${false}
        connectionState="disconnected"
      ></runefoble-voice-controls>
    </div>
  `,
};

export const WaveformActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls
        .isListening=${true}
        .simulated=${true}
        connectionState="connected"
        .bitrateKbps=${64}
        .latencyMs=${22}
      ></runefoble-voice-controls>
    </div>
  `,
};

export const LowBandwidthWarning: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls
        .isListening=${true}
        .simulated=${true}
        connectionState="connected"
        bandwidthQuality="low"
        .bitrateKbps=${16}
        .packetsLost=${14}
        .latencyMs=${195}
      ></runefoble-voice-controls>
    </div>
  `,
};

export const AfflictionDspActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-voice-controls
        .isListening=${true}
        .simulated=${true}
        connectionState="connected"
        .activeFilters=${['drunk', 'slur_articulation']}
        .bitrateKbps=${64}
        .latencyMs=${28}
      ></runefoble-voice-controls>
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
