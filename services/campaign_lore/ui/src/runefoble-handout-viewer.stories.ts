import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-handout-viewer.ts';

const meta: Meta = {
  title: 'CampaignLore/RunefobleHandoutViewer',
  component: 'runefoble-handout-viewer',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const SealedRoyalDecree: Story = {
  render: () => html`
    <runefoble-handout-viewer
      title="Royal Decree of Neverwinter"
      handoutType="decree"
      paperTexture="weathered_parchment"
      calligraphyFont="royal_chancery"
      content="Hear ye, champions of the realm. The deep crypts of Mount Hotenow have begun to shudder. Form ranks at the southern gate before the solstice dusk."
      .hasWaxSeal=${true}
      sealState="intact"
      sealColor="crimson"
      sealStamp="raven_crest"
      .hasInvisibleInk=${true}
      secretInkText="BEWARE: THE LORD OF EMBERS WEARS THE MAYOR'S FACE"
    ></runefoble-handout-viewer>
  `,
};

export const BrokenBountyNotice: Story = {
  render: () => html`
    <runefoble-handout-viewer
      title="Wanted: The Whisperer in Shadows"
      handoutType="bounty"
      paperTexture="ancient_papyrus"
      calligraphyFont="cursed_blackletter"
      content="WANTED DEAD OR ALIVE: 5,000 Gold Sovereigns for the capture of the warlock Malkor. Known to frequent the Sunken Spire docks."
      .hasWaxSeal=${true}
      sealState="broken"
      sealColor="obsidian"
    ></runefoble-handout-viewer>
  `,
};

export const SecretRunicCipher: Story = {
  render: () => html`
    <runefoble-handout-viewer
      title="Ancient Crypt Scroll"
      handoutType="crypt_map"
      paperTexture="royal_vellum"
      calligraphyFont="elvish_script"
      content="To find the path where waters divide, look not to the stars, but to the roots."
      .hasWaxSeal=${false}
      .hasInvisibleInk=${true}
      .uvMode=${true}
      secretInkText="KHAR-DRAK-MOR: THREE TURNS COUNTER-CLOCKWISE"
    ></runefoble-handout-viewer>
  `,
};
