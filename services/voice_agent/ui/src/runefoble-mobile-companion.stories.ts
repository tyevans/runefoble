import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-mobile-companion.ts';
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
      <runefoble-mobile-companion
        .connected=${true}
        userId="marcus"
        channelName="Party Voice (Cellular Opus)"
        audioTier="mobile_optimized"
        .sampleRate=${16000}
        .bitrateKbps=${16}
        .bufferHealthMs=${48}
        .packetLoss=${0.01}
        .bandwidthKbps=${150}
      ></runefoble-mobile-companion>
    </div>
  `,
};

export const SecretWhisperActive: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion
        .connected=${true}
        userId="marcus"
        channelName="Party Voice (Cellular Opus)"
        audioTier="mobile_optimized"
        .sampleRate=${16000}
        .bitrateKbps=${16}
        .bufferHealthMs=${42}
        .privacyBlur=${true}
        .activeWhisper=${{
          sender: 'The Watcher',
          content:
            'You feel cold breath upon the back of your neck. Something lurks behind the sarcophagus.',
          timestamp: '2026-09-26T19:50:00Z',
        }}
      ></runefoble-mobile-companion>
    </div>
  `,
};

export const ConstrainedCellularFallback: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion
        .connected=${true}
        userId="marcus"
        channelName="Party Voice (Cellular Opus)"
        audioTier="cellular_constrained"
        .sampleRate=${16000}
        .bitrateKbps=${12}
        .bufferHealthMs=${15}
        .packetLoss=${0.08}
        .bandwidthKbps=${38}
      ></runefoble-mobile-companion>
    </div>
  `,
};

export const TurnAlertPrompt: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion
        .connected=${true}
        userId="marcus"
        channelName="Party Voice (Cellular Opus)"
        audioTier="mobile_optimized"
        .turnAlertActive=${true}
        turnAlertText="Round 3: It's Marcus's turn to act in initiative order!"
      ></runefoble-mobile-companion>
    </div>
  `,
};

export const OfflineDisconnected: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 500px; background: #0f172a;">
      <runefoble-mobile-companion
        .connected=${false}
        userId="marcus"
        channelName="Party Voice (Cellular Opus)"
        audioTier="mobile_optimized"
        .sampleRate=${16000}
        .bitrateKbps=${0}
        .bufferHealthMs=${0}
      ></runefoble-mobile-companion>
    </div>
  `,
};

export const InteractiveSimulator: Story = {
  render: () => {
    const handleSimWhisper = () => {
      const comp = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (comp) {
        comp.receiveWhisper({
          sender: 'The Watcher',
          content: 'An invisible stalker glides silently toward your blind spot.',
          timestamp: new Date().toISOString(),
        });
      }
    };

    const handleSimHaptic = () => {
      const comp = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (comp) {
        comp.triggerHaptic([300, 150, 300], 'turn_alert');
      }
    };

    const handleToggleNetwork = () => {
      const comp = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (comp) {
        if (comp.audioTier === 'mobile_optimized') {
          comp.audioTier = 'cellular_constrained';
          comp.bitrateKbps = 12;
          comp.packetLoss = 0.09;
          comp.bufferHealthMs = 18;
        } else {
          comp.audioTier = 'mobile_optimized';
          comp.bitrateKbps = 16;
          comp.packetLoss = 0.01;
          comp.bufferHealthMs = 46;
        }
      }
    };

    const handleToggleOnline = () => {
      const comp = document.querySelector('runefoble-mobile-companion') as RunefobleMobileCompanion;
      if (comp) {
        comp.connected = !comp.connected;
      }
    };

    return html`
      <div style="padding: 24px; max-width: 500px; background: #0f172a; display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button style="padding: 6px 12px; cursor: pointer; font-weight: bold;" @click=${handleSimWhisper}>
            🤫 Sim Whisper
          </button>
          <button style="padding: 6px 12px; cursor: pointer; font-weight: bold;" @click=${handleSimHaptic}>
            📳 Sim Haptic Buzz
          </button>
          <button style="padding: 6px 12px; cursor: pointer; font-weight: bold;" @click=${handleToggleNetwork}>
            📶 Toggle Network Surge
          </button>
          <button style="padding: 6px 12px; cursor: pointer; font-weight: bold;" @click=${handleToggleOnline}>
            🔌 Toggle Online
          </button>
        </div>
        <runefoble-mobile-companion
          .connected=${true}
          userId="marcus"
          channelName="Party Voice (Cellular Opus)"
          audioTier="mobile_optimized"
          .sampleRate=${16000}
          .bitrateKbps=${16}
          .bufferHealthMs=${45}
        ></runefoble-mobile-companion>
      </div>
    `;
  },
};
