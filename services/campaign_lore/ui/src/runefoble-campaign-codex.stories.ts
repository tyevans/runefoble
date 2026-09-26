import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-codex.ts';
import type { LoreEntry } from './runefoble-campaign-codex.ts';

const meta: Meta = {
  title: 'CampaignLore/RunefobleCampaignCodex',
  component: 'runefoble-campaign-codex',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleEntries: LoreEntry[] = [
  {
    id: 'lore-1',
    title: 'The Order of the Silver Dawn',
    text: 'Sir Gareth, also known as The Silver Knight, commands the garrison guarding the Citadel of Light in Neverwinter.',
    entities: ['Sir Gareth', 'The Silver Knight', 'Citadel of Light', 'Neverwinter'],
    graphContext: ['Sir Gareth --[guards]--> Citadel of Light', 'Citadel of Light --[located in]--> Neverwinter'],
    isSecret: false,
  },
  {
    id: 'lore-2',
    title: 'Secret Cult of the Red Moon',
    text: 'A secret splinter cabal beneath Neverwinter plans to poison the Well of Resplendence during the solstice.',
    entities: ['Cult of the Red Moon', 'Well of Resplendence', 'Neverwinter'],
    graphContext: ['Cult of the Red Moon --[targets]--> Well of Resplendence'],
    isSecret: true,
  },
];

export const PlayerView: Story = {
  render: () => html`
    <runefoble-campaign-codex
      campaignId="campaign-demo"
      .isDM=${false}
      .entries=${sampleEntries}
    ></runefoble-campaign-codex>
  `,
};

export const DMSecretView: Story = {
  render: () => html`
    <runefoble-campaign-codex
      campaignId="campaign-demo"
      .isDM=${true}
      .entries=${sampleEntries}
    ></runefoble-campaign-codex>
  `,
};
