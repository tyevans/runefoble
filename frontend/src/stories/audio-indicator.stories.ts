import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-audio-indicator.ts';

const meta: Meta = {
  title: 'Voice/RunefobleAudioIndicator',
  component: 'runefoble-audio-indicator',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultIdle: Story = {
  render: () => html`
    <div
      style="
        padding: 24px;
        background: var(--rf-bg-canvas, #f8f9fa);
        border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
        max-width: 480px;
      "
    >
      <runefoble-audio-indicator
        peerName="Valeros (Fighter)"
        role="player"
        .audioLevel=${0.0}
        .isSpeaking=${false}
      ></runefoble-audio-indicator>
    </div>
  `,
};

export const LiveSpeakingDungeonMaster: Story = {
  render: () => html`
    <div
      style="
        padding: 24px;
        background: var(--rf-bg-canvas, #f8f9fa);
        border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
        max-width: 480px;
      "
    >
      <runefoble-audio-indicator
        peerName="The Watcher"
        role="dungeon_master"
        .audioLevel=${0.75}
        .isSpeaking=${true}
        .activeFilters=${['cavern_reverb']}
      ></runefoble-audio-indicator>
    </div>
  `,
};

export const MutedWithSessionPenalties: Story = {
  render: () => html`
    <div
      style="
        padding: 24px;
        background: var(--rf-bg-canvas, #f8f9fa);
        border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
        max-width: 480px;
      "
    >
      <runefoble-audio-indicator
        peerName="Kyra (Cleric Stand-in)"
        role="player"
        .audioLevel=${0.0}
        .isSpeaking=${false}
        .isMuted=${true}
        .activeFilters=${['drunk', 'underwater']}
      ></runefoble-audio-indicator>
    </div>
  `,
};
