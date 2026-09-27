import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-mobile-companion.ts';
import './mobile_companion/index.ts';
import type { RunefobleMobileCompanion } from './runefoble-mobile-companion.ts';

const meta: Meta = {
  title: 'Voice/RunefobleMobileCompanion',
  component: 'runefoble-mobile-companion',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultConnected: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion .connected=${true} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="mobile_optimized" .sampleRate=${16000} .bitrateKbps=${16} .bufferHealthMs=${48} .packetLoss=${0.01} .bandwidthKbps=${150}></runefoble-mobile-companion>
    </div>
  `,
};

export const SecretWhisperActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion .connected=${true} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="mobile_optimized" .sampleRate=${16000} .bitrateKbps=${16} .bufferHealthMs=${42} .privacyBlur=${true} .activeWhisper=${{ sender: 'The Watcher', content: 'You feel cold breath upon the back of your neck. Something lurks behind the sarcophagus.', timestamp: '2026-09-26T19:50:00Z' }}></runefoble-mobile-companion>
    </div>
  `,
};

export const ConstrainedCellularFallback: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion .connected=${true} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="cellular_constrained" .sampleRate=${16000} .bitrateKbps=${12} .bufferHealthMs=${15} .packetLoss=${0.08} .bandwidthKbps=${38}></runefoble-mobile-companion>
    </div>
  `,
};

export const TurnAlertPrompt: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion .connected=${true} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="mobile_optimized" .turnAlertActive=${true} turnAlertText="Round 3: It's Marcus's turn to act in initiative order!"></runefoble-mobile-companion>
    </div>
  `,
};

export const OfflineDisconnected: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion .connected=${false} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="mobile_optimized" .sampleRate=${16000} .bitrateKbps=${0} .bufferHealthMs=${0}></runefoble-mobile-companion>
    </div>
  `,
};

export const AudioStreamControllerStory: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <audio-stream-controller channelName="Party Voice (Cellular Opus)" .sampleRate=${16000} .bitrateKbps=${16} .bufferHealthMs=${45} .packetLoss=${0.02} .bandwidthKbps=${120}></audio-stream-controller>
    </div>
  `,
};

export const HapticPingPanelStory: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <haptic-ping-panel .turnAlertActive=${true} turnAlertText="Your turn in combat!" .activeWhisper=${{ sender: 'The Watcher', content: 'A shadow falls across the chamber doorway.' }}></haptic-ping-panel>
    </div>
  `,
};

export const ConnectionStatusBadgeStory: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <connection-status-badge .connected=${true} audioTier="mobile_optimized" .isVibrating=${true} .latencyMs=${42}></connection-status-badge>
    </div>
  `,
};

export const InteractiveSimulator: Story = {
  render: () => {
    const simWhisper = () => (document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion)?.receiveWhisper({ sender: 'The Watcher', content: 'An invisible stalker glides silently toward your blind spot.', timestamp: new Date().toISOString() });
    const simHaptic = () => (document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion)?.triggerHaptic([300, 150, 300], 'turn_alert');
    const toggleNet = () => {
      const c = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (c) {
        c.audioTier = c.audioTier === 'mobile_optimized' ? 'cellular_constrained' : 'mobile_optimized';
        c.bitrateKbps = c.audioTier === 'mobile_optimized' ? 16 : 12;
        c.bufferHealthMs = c.audioTier === 'mobile_optimized' ? 46 : 18;
      }
    };
    const toggleOnline = () => {
      const c = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (c) c.connected = !c.connected;
    };
    return html`
      <div style="padding: 24px; max-width: 500px; background: #0f172a; display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button style="padding: 6px 12px; cursor: pointer;" @click=${simWhisper}>🤫 Sim Whisper</button>
          <button style="padding: 6px 12px; cursor: pointer;" @click=${simHaptic}>📳 Sim Haptic</button>
          <button style="padding: 6px 12px; cursor: pointer;" @click=${toggleNet}>📶 Toggle Network</button>
          <button style="padding: 6px 12px; cursor: pointer;" @click=${toggleOnline}>🔌 Toggle Online</button>
        </div>
        <runefoble-mobile-companion .connected=${true} userId="marcus" channelName="Party Voice (Cellular Opus)" audioTier="mobile_optimized" .sampleRate=${16000} .bitrateKbps=${16} .bufferHealthMs=${45}></runefoble-mobile-companion>
      </div>
    `;
  },
};
