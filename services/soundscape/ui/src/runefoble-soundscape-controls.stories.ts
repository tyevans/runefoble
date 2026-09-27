import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-soundscape-controls.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleSoundscapeControls',
  component: 'runefoble-soundscape-controls',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ExplorationDefault: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="15"
      stemProfile="exploration"
      masterVolume="80"
    ></runefoble-soundscape-controls>
  `,
};

export const QuietAmbient: Story = ExplorationDefault;

export const TensionRising: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="48"
      stemProfile="tension"
      masterVolume="85"
    ></runefoble-soundscape-controls>
  `,
};

export const CombatActive: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="74"
      stemProfile="combat"
      masterVolume="90"
    ></runefoble-soundscape-controls>
  `,
};

export const HighTensionCombat: Story = CombatActive;

export const BossClimax: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="96"
      stemProfile="boss"
      masterVolume="100"
    ></runefoble-soundscape-controls>
  `,
};

export const VoiceDuckingActive: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="65"
      stemProfile="combat"
      masterVolume="85"
      .isDucked=${true}
    ></runefoble-soundscape-controls>
  `,
};

export const ActiveFoleyPlayback: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="60"
      stemProfile="combat"
      masterVolume="85"
    ></runefoble-soundscape-controls>
  `,
};

export const ManualMoodOverride: Story = {
  render: () => html`
    <runefoble-soundscape-controls
      sessionId="session-tomb-14"
      tensionScore="30"
      stemProfile="boss"
      .manualOverride=${true}
      masterVolume="85"
    ></runefoble-soundscape-controls>
  `,
};
