import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-character-roster.ts';
import type { CharacterItem, RosterCampaignOption } from './types.ts';

const meta: Meta = {
  title: 'CharacterSheet/CharacterRoster',
  component: 'runefoble-character-roster',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleCampaigns: RosterCampaignOption[] = [
  { id: 'camp-101', title: 'Tomb of the Star-Eater' },
  { id: 'camp-102', title: 'Whispering Depths' },
  { id: 'camp-103', title: 'Curse of the Crimson Citadel' },
];

const sampleCharacters: CharacterItem[] = [
  {
    id: 'char-1',
    name: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    subclass: 'Battle Master',
    level: 4,
    currentHp: 38,
    maxHp: 45,
    armorClass: 18,
    speed: 30,
    campaignId: 'camp-101',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-2',
    name: 'Kyra the Sun Maiden',
    characterClass: 'Cleric',
    subclass: 'Life Domain',
    level: 4,
    currentHp: 28,
    maxHp: 32,
    armorClass: 16,
    speed: 25,
    campaignId: 'camp-101',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/cleric.svg',
  },
  {
    id: 'char-3',
    name: 'Ezren the Gray',
    characterClass: 'Wizard',
    subclass: 'Evocation',
    level: 5,
    currentHp: 8,
    maxHp: 26,
    armorClass: 12,
    speed: 30,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
  {
    id: 'char-4',
    name: 'Merisiel Nightshadow',
    characterClass: 'Rogue',
    subclass: 'Thief',
    level: 3,
    currentHp: 22,
    maxHp: 22,
    armorClass: 15,
    speed: 35,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/rogue.svg',
  },
];

export const PopulatedRoster: Story = {
  render: () => html`
    <runefoble-character-roster
      .characters=${sampleCharacters}
      .campaigns=${sampleCampaigns}
    ></runefoble-character-roster>
  `,
};

export const EmptyRoster: Story = {
  render: () => html`
    <runefoble-character-roster
      .characters=${[]}
      .campaigns=${sampleCampaigns}
    ></runefoble-character-roster>
  `,
};

export const FilteredAssigned: Story = {
  render: () => html`
    <runefoble-character-roster
      .characters=${sampleCharacters}
      .campaigns=${sampleCampaigns}
      active-filter="assigned"
    ></runefoble-character-roster>
  `,
};

export const FilteredUnassigned: Story = {
  render: () => html`
    <runefoble-character-roster
      .characters=${sampleCharacters}
      .campaigns=${sampleCampaigns}
      active-filter="unassigned"
    ></runefoble-character-roster>
  `,
};
