import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-mobile-companion.ts';

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
        audioTier="mobile_optimized"
        .sampleRate=${16000}
        .bitrateKbps=${16}
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
        audioTier="mobile_optimized"
        .sampleRate=${16000}
        .bitrateKbps=${16}
        .activeWhisper=${{
          sender: 'The Watcher',
          content: 'You feel cold breath upon the back of your neck. Something lurks behind the sarcophagus.',
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
        audioTier="cellular_constrained"
        .sampleRate=${16000}
        .bitrateKbps=${12}
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
        audioTier="mobile_optimized"
        .turnAlertActive=${true}
        turnAlertText="Round 3: It's Marcus's turn to act in initiative order!"
      ></runefoble-mobile-companion>
    </div>
  `,
};
