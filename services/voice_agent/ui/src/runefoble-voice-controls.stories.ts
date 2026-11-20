import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-voice-controls.ts';

/**
 * Push to Talk states (TASK-0946). The App Shell sets `sending`, `transcript`, `watcherError`
 * and `uploadError` from the transcribe reply. The stories set them directly. No story opens
 * the microphone until the reader holds the button.
 */
const meta: Meta = {
  title: 'Voice/RunefobleVoiceControls',
  component: 'runefoble-voice-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const frame = (content: unknown) => html`
  <div style="padding: 24px; max-width: 800px; background: var(--rf-bg-canvas, #f8f9fa);">${content}</div>
`;

export const Idle: Story = {
  render: () => frame(html`<runefoble-voice-controls></runefoble-voice-controls>`),
};

export const Holding: Story = {
  render: () => frame(html`<runefoble-voice-controls .holding=${true}></runefoble-voice-controls>`),
};

export const Sending: Story = {
  render: () => frame(html`<runefoble-voice-controls .sending=${true}></runefoble-voice-controls>`),
};

export const TranscriptShown: Story = {
  render: () =>
    frame(html`<runefoble-voice-controls .transcript=${'Move my warrior two squares north'}></runefoble-voice-controls>`),
};

export const TranscriptWithWatcherError: Story = {
  render: () =>
    frame(html`<runefoble-voice-controls
      .transcript=${'Move my warrior two squares north'}
      .watcherError=${'The Watcher answered 503'}
    ></runefoble-voice-controls>`),
};

export const UploadError: Story = {
  render: () =>
    frame(html`<runefoble-voice-controls
      .uploadError=${'Push to Talk failed (503): The speech engine is unavailable.'}
    ></runefoble-voice-controls>`),
};

export const AfflictionDspActive: Story = {
  render: () =>
    frame(html`<runefoble-voice-controls .activeFilters=${['drunk', 'slur_articulation']}></runefoble-voice-controls>`),
};

export const CustomChannelDisabled: Story = {
  render: () =>
    frame(html`<runefoble-voice-controls .channelName=${'Spectator Whispers'} .disabled=${true}></runefoble-voice-controls>`),
};
