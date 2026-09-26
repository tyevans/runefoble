import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-rules-compendium.ts';
import './runefoble-rules-lookup.ts';
import './runefoble-encounter-builder.ts';
import type { DraftMonsterEntry, RuleSearchResultItem } from './types.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleRulesCompendium',
  component: 'runefoble-rules-compendium',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const SAMPLE_SEARCH_RESULTS: RuleSearchResultItem[] = [
  {
    category: 'monster',
    name: 'Goblin',
    score: 0.95,
    summary: 'Small humanoid (goblinoid), neutral evil. Agile skirmisher known for nimble escapes.',
    details: {
      challenge_rating: 0.25,
      xp: 50,
      role: 'skirmisher',
      armor_class: 15,
      hit_points: 7,
      speed: '30 ft.',
      stats: { STR: 8, DEX: 14, CON: 10, INT: 10, WIS: 8, CHA: 8 },
      description: 'Nimble Escape: Disengage or Hide as a bonus action.',
    },
    is_homebrew: false,
    campaign_id: null,
  },
  {
    category: 'spell',
    name: 'Fireball',
    score: 0.92,
    summary: 'A bright streak flashes from your pointing finger to a point you choose and blossoms with a low roar into an explosion of flame.',
    details: {
      level: 3,
      school: 'Evocation',
      casting_time: '1 action',
      range: '150 feet',
      duration: 'Instantaneous',
      description: 'Each creature in a 20-foot-radius sphere must make a Dexterity saving throw, taking 8d6 fire damage on a failed save.',
    },
    is_homebrew: false,
    campaign_id: null,
  },
  {
    category: 'condition',
    name: 'Paralyzed',
    score: 0.88,
    summary: 'A paralyzed creature is incapacitated and can’t move or speak. Attacks against it have advantage, and hits within 5 feet are critical.',
    details: {
      effects: [
        'Incapacitated (can’t take actions or reactions)',
        'Speed is 0 and can’t benefit from bonuses to speed',
        'Automatically fails Strength and Dexterity saving throws',
        'Attack rolls against the creature have advantage',
      ],
      description: 'Total motor immobilization through venom, magic, or psionic shock.',
    },
    is_homebrew: false,
    campaign_id: null,
  },
  {
    category: 'monster',
    name: 'Abyssal Shadowstalker',
    score: 0.85,
    summary: 'Medium fiend, neutral evil. A stealthy predator bred in the shadow trenches.',
    details: {
      challenge_rating: 3.0,
      xp: 700,
      role: 'skirmisher',
      armor_class: 16,
      hit_points: 45,
      speed: '40 ft.',
      stats: { STR: 14, DEX: 18, CON: 14, INT: 12, WIS: 14, CHA: 10 },
      description: 'Shadow Camouflage: Has advantage on Stealth checks in dim light or darkness.',
    },
    is_homebrew: true,
    campaign_id: 'camp-shadow-99',
  },
];

const SAMPLE_DRAFT_MONSTERS: DraftMonsterEntry[] = [
  { name: 'Goblin', cr: 0.25, xp: 50, role: 'skirmisher', count: 4 },
  { name: 'Bugbear', cr: 1.0, xp: 200, role: 'brute', count: 1 },
];

export const Default: Story = {
  render: () => html`
    <runefoble-rules-compendium
      .campaignId=${'campaign-sunken-tomb'}
      .partyLevels=${[3, 3, 3, 3]}
      .targetDifficulty=${'Medium'}
      .draftMonsters=${SAMPLE_DRAFT_MONSTERS}
    ></runefoble-rules-compendium>
  `,
};

export const SearchResultsWithLatency: Story = {
  render: () => html`
    <runefoble-rules-lookup
      .campaignId=${'campaign-sunken-tomb'}
      .results=${SAMPLE_SEARCH_RESULTS}
      .tookMs=${1.45}
    ></runefoble-rules-lookup>
  `,
};

export const MonsterStatCards: Story = {
  render: () => html`
    <runefoble-rules-lookup
      .results=${SAMPLE_SEARCH_RESULTS}
      .tookMs=${2.1}
      .selectedCategory=${'monster'}
    ></runefoble-rules-lookup>
  `,
};

export const CREncounterBalanceCalculator: Story = {
  render: () => html`
    <runefoble-encounter-builder
      .campaignId=${'campaign-sunken-tomb'}
      .partyLevels=${[4, 4, 4, 4]}
      .targetDifficulty=${'Hard'}
      .draftMonsters=${[
        { name: 'Ogre', cr: 2.0, xp: 450, role: 'brute', count: 2 },
        { name: 'Goblin', cr: 0.25, xp: 50, role: 'skirmisher', count: 3 },
      ]}
    ></runefoble-encounter-builder>
  `,
};

export const HomebrewCreator: Story = {
  render: () => html`
    <runefoble-rules-compendium
      .campaignId=${'campaign-homebrew-lab'}
      .userId=${'dm-evelyn'}
      .isDM=${true}
      .activeTab=${'homebrew'}
    ></runefoble-rules-compendium>
  `,
};
