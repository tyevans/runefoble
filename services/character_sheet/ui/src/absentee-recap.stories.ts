import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-absentee-recap.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleAbsenteeRecap',
  component: 'runefoble-absentee-recap',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DrunkCleric: Story = {
  render: () => html`
    <runefoble-absentee-recap
      characterName="Kyra the Dawnflower"
      persona="scholarly"
      .penalties=${['drunk']}
      narrative="Welcome back, Kyra! While you were away, The Watcher piloted your cleric under the scholarly persona. Severely impaired by an overabundance of tavern spirits ('drunk'), Kyra swayed violently across the battlefield, belting out slurred hymns between hiccups and swinging at flagstones. Yet miraculously, an accidental stumble tripped an encroaching hobgoblin lieutenant, saving the frontline."
      .highlights=${[
        'Swayed on heels while quoting sacred texts with slurred fervor.',
        'Tripped over a tavern bench, knocking out an oncoming hobgoblin.',
        'Spilled blessed vintage onto a wounded rogue, accidentally curing 4 HP.',
      ]}
      .hpDelta=${-3}
      .itemsAcquired=${['Half-empty Dwarven Flagon', 'Tarnished Silver Bell']}
      .isPlayingAudio=${false}
    ></runefoble-absentee-recap>
  `,
};

export const FoolishRogue: Story = {
  render: () => html`
    <runefoble-absentee-recap
      characterName="Merisiel of the Shadows"
      persona="impulsive"
      .penalties=${['foolishness', 'greed']}
      narrative="Welcome back, Merisiel! While you were away, The Watcher assumed control. Afflicted with boundless foolishness, Merisiel mistook a snarling bugbear for an ornate coat rack and hung her leather jerkin upon its horns. Driven by brazen greed, she simultaneously pocketed glowing cursed copper coins while allies desperately ducked under swinging greataxes."
      .highlights=${[
        'Mistook an armored bugbear sentry for a coat rack.',
        'Ignored tactical cover to lecture enemies on lockpicking geometry.',
        'Pocketed 14 suspiciously warm copper coins from an ancient sacrificial urn.',
        'Dived through a stained-glass window to catch a rolling brass button.',
      ]}
      .hpDelta=${-7}
      .itemsAcquired=${['Cursed Copper Coins (x14)', 'Gilded Brass Button']}
      .isPlayingAudio=${true}
    ></runefoble-absentee-recap>
  `,
};

export const BattleReadyFighter: Story = {
  render: () => html`
    <runefoble-absentee-recap
      characterName="Valeros the Steadfast"
      persona="valiant"
      .penalties=${[]}
      narrative="Welcome back, Valeros! While you were away from the realm, The Watcher piloted your warrior with textbook discipline. Holding the shield wall with unwavering resolve, Valeros absorbed enemy charges and kept the rear spellcasters protected without suffering a scratch."
      .highlights=${[
        'Held the dungeon corridor chokepoint against 5 cave goblins.',
        'Coordinated defensive maneuvers keeping the party intact.',
        'Returned with all weapons and vital organs in pristine condition.',
      ]}
      .hpDelta=${0}
      .itemsAcquired=${['Ornate Steel Gauntlets']}
      .isPlayingAudio=${false}
    ></runefoble-absentee-recap>
  `,
};
