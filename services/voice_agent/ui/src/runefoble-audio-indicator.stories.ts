import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-audio-indicator.ts';

const meta: Meta = {
  title: 'Voice/RunefobleAudioIndicator',
  component: 'runefoble-audio-indicator',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const IdlePlayer: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 400px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-audio-indicator
        peerName="Valeros"
        role="player"
        .audioLevel=${0.0}
        .isSpeaking=${false}
      ></runefoble-audio-indicator>
    </div>
  `,
};

export const ActiveSpeakingDungeonMaster: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 400px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-audio-indicator
        peerName="The Watcher"
        role="dungeon_master"
        .audioLevel=${0.68}
        .isSpeaking=${true}
        .activeFilters=${['cavern_reverb']}
      ></runefoble-audio-indicator>
    </div>
  `,
};

export const MutedWithConditionDSP: Story = {
  render: () => html`
    <div style="padding: 24px; max-width: 400px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-audio-indicator
        peerName="Kyra (Stand-in)"
        role="player"
        .audioLevel=${0.0}
        .isSpeaking=${false}
        .isMuted=${true}
        .activeFilters=${['drunk', 'underwater']}
      ></runefoble-audio-indicator>
    </div>
  `,
};
