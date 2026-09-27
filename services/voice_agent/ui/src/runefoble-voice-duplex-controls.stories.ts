import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-voice-duplex-controls.ts';

const meta: Meta = {
  title: 'Voice/RunefobleVoiceDuplexControls',
  component: 'runefoble-voice-duplex-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const IdleStandby: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .isListening=${false}
        .isPlaybackActive=${false}
        .isInterrupted=${false}
        .isDmMuted=${false}
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};

export const PlaybackActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .isListening=${false}
        .isPlaybackActive=${true}
        .isInterrupted=${false}
        .isDmMuted=${false}
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};

export const PlayerBargeInInterjection: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .isListening=${true}
        .isPlaybackActive=${false}
        .isInterrupted=${true}
        .isDmMuted=${true}
        .interruptionLatencyMs=${64}
        .micLevel=${0.82}
        remainingNarration="The shadow dragon breathes a cone of dark fire..."
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};

export const DmMutedWithCrossfade: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .isListening=${true}
        .isPlaybackActive=${false}
        .isInterrupted=${true}
        .isDmMuted=${true}
        .crossfadeActive=${true}
        .interruptionLatencyMs=${48}
        .micLevel=${0.68}
        remainingNarration="...shattering the cavern wall into dust."
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};

export const VADCalibrationSettings: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .showSettings=${true}
        .vadSensitivity=${85}
        .duckingGainDb=${-18}
        .aecEnabled=${true}
        .aecSuppressionDb=${42}
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};

export const InteractiveSimulator: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 640px; background: var(--rf-bg-canvas, #f4f4f5);">
      <runefoble-voice-duplex-controls
        .isConnected=${true}
        .isListening=${true}
        .micLevel=${0.55}
        .showSettings=${false}
      ></runefoble-voice-duplex-controls>
    </div>
  `,
};
