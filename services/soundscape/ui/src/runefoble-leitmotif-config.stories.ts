import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-leitmotif-config.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleLeitmotifConfig',
  component: 'runefoble-leitmotif-config',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultNadiaLute: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-nadia"
      characterName="Nadia"
      instrumentTimbre="lute"
      tempoMultiplier="1.05"
      volumeGain="100"
    ></runefoble-leitmotif-config>
  `,
};

export const HeroicBrass: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-valeros"
      characterName="Valeros"
      instrumentTimbre="brass"
      tempoMultiplier="1.0"
      volumeGain="110"
    ></runefoble-leitmotif-config>
  `,
};

export const SomberCelloStrings: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-kyra"
      characterName="Kyra"
      instrumentTimbre="strings"
      tempoMultiplier="0.95"
      volumeGain="95"
    ></runefoble-leitmotif-config>
  `,
};

export const ArcaneSynth: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-ezren"
      characterName="Ezren"
      instrumentTimbre="synth"
      tempoMultiplier="1.1"
      volumeGain="90"
    ></runefoble-leitmotif-config>
  `,
};

export const VoiceDuckingActive: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-nadia"
      characterName="Nadia"
      instrumentTimbre="lute"
      tempoMultiplier="1.05"
      volumeGain="100"
      .isDucked=${true}
    ></runefoble-leitmotif-config>
  `,
};

export const AuditionPlaying: Story = {
  render: () => html`
    <runefoble-leitmotif-config
      sessionId="session-tomb-14"
      characterId="char-nadia"
      characterName="Nadia"
      instrumentTimbre="lute"
      tempoMultiplier="1.05"
      volumeGain="100"
      .activePlayingMotif=${'triumphant'}
    ></runefoble-leitmotif-config>
  `,
};
