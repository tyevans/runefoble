import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '@runefoble/ui-core/story-auth-provider';
import { installTokenCheckingFetch } from '@runefoble/ui-core/story-fetch';
import './runefoble-rules-compendium.ts';
import './runefoble-rules-lookup.ts';
import './runefoble-encounter-builder.ts';
import './runefoble-homebrew-creator.ts';
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

/** The #/rules route. No campaign id, so the compendium offers search and the encounter builder only. */
export const SrdOnlyWithoutHomebrew: Story = {
  render: () => html`
    <runefoble-rules-compendium></runefoble-rules-compendium>
  `,
};

/** The campaign rules route. The campaign id is set, so the homebrew forge tab is offered. */
export const CampaignRulesWithHomebrew: Story = {
  render: () => html`
    <runefoble-rules-compendium
      .campaignId=${'campaign-homebrew-lab'}
      .isDM=${true}
    ></runefoble-rules-compendium>
  `,
};

export const DedicatedHomebrewCreator: Story = {
  render: () => html`
    <runefoble-homebrew-creator
      .campaignId=${'campaign-homebrew-lab'}
      .isDM=${true}
    ></runefoble-homebrew-creator>
  `,
};


const AUTH_SEARCH_RESPONSE = { results: SAMPLE_SEARCH_RESULTS, took_ms: 12.5 };

export const RulesLookupWithShellAuth: Story = {
  render: () => {
    installTokenCheckingFetch('story-token', AUTH_SEARCH_RESPONSE);
    return html`
      <runefoble-story-auth-provider token="story-token">
        <runefoble-rules-lookup apiBaseUrl="http://story.invalid"></runefoble-rules-lookup>
      </runefoble-story-auth-provider>
    `;
  },
};

export const RulesLookupNoAuthProviderShowsError: Story = {
  render: () => {
    installTokenCheckingFetch('story-token', AUTH_SEARCH_RESPONSE);
    return html`<runefoble-rules-lookup apiBaseUrl="http://story.invalid"></runefoble-rules-lookup>`;
  },
};

export const HomebrewCreatorWithShellAuth: Story = {
  render: () => {
    installTokenCheckingFetch('story-token', { rule_id: 'hb-1', title: 'Story Rule', status: 'registered' });
    return html`
      <runefoble-story-auth-provider token="story-token">
        <runefoble-homebrew-creator apiBaseUrl="http://story.invalid" .campaignId=${'campaign-homebrew-lab'}></runefoble-homebrew-creator>
      </runefoble-story-auth-provider>
    `;
  },
};

export const HomebrewCreatorNoAuthProviderShowsError: Story = {
  render: () => {
    installTokenCheckingFetch('story-token', { rule_id: 'hb-1', title: 'Story Rule', status: 'registered' });
    return html`<runefoble-homebrew-creator apiBaseUrl="http://story.invalid" .campaignId=${'campaign-homebrew-lab'}></runefoble-homebrew-creator>`;
  },
};

/** Replaces window.fetch for one story. Returns a restore function and the requests seen. */
function stubHomebrewFetch(status: number, body: unknown) {
  const original = window.fetch;
  const requests: { url: string; auth: string | null }[] = [];
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    requests.push({ url: String(input), auth: new Headers(init?.headers).get('Authorization') });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  };
  return { requests, restore: () => { window.fetch = original; } };
}

async function waitForText(root: ShadowRoot | null, text: string): Promise<void> {
  for (let i = 0; i < 100; i++) {
    if (root?.textContent?.includes(text)) return;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(`Expected the form to show "${text}"`);
}

/** Fills the title, submits the form, and returns the element's shadow root. */
async function submitHomebrewTitle(canvasElement: HTMLElement, title: string): Promise<ShadowRoot> {
  const el = canvasElement.querySelector('runefoble-homebrew-creator') as HTMLElement;
  const root = el.shadowRoot as ShadowRoot;
  const input = root.querySelector('input.form-input') as HTMLInputElement;
  input.value = title;
  input.dispatchEvent(new Event('input'));
  (root.querySelector('form') as HTMLFormElement).requestSubmit();
  return root;
}

export const HomebrewRegisteredState: Story = {
  render: () => html`
    <runefoble-story-auth-provider token="story-token">
      <runefoble-homebrew-creator apiBaseUrl="http://story.invalid" .campaignId=${'campaign-homebrew-lab'}></runefoble-homebrew-creator>
    </runefoble-story-auth-provider>
  `,
  play: async ({ canvasElement }) => {
    const stub = stubHomebrewFetch(200, { rule_id: 'hb-7', campaign_id: 'campaign-homebrew-lab', author_id: 'dm-evelyn', rule_type: 'monster', title: 'Abyssal Stalker', content: {}, status: 'registered' });
    try {
      const root = await submitHomebrewTitle(canvasElement, 'Abyssal Stalker');
      await waitForText(root, 'Registered "Abyssal Stalker" successfully!');
      if (stub.requests[0]?.url !== 'http://story.invalid/api/v1/compendium/homebrew') throw new Error(`Wrong URL: ${stub.requests[0]?.url}`);
      if (stub.requests[0]?.auth !== 'Bearer story-token') throw new Error(`Missing bearer: ${stub.requests[0]?.auth}`);
    } finally {
      stub.restore();
    }
  },
};

export const HomebrewServerErrorState: Story = {
  render: () => html`
    <runefoble-story-auth-provider token="story-token">
      <runefoble-homebrew-creator apiBaseUrl="http://story.invalid" .campaignId=${'campaign-homebrew-lab'}></runefoble-homebrew-creator>
    </runefoble-story-auth-provider>
  `,
  play: async ({ canvasElement }) => {
    const stub = stubHomebrewFetch(503, { detail: 'Registration is unavailable. Try again later.' });
    try {
      const root = await submitHomebrewTitle(canvasElement, 'Abyssal Stalker');
      await waitForText(root, 'Registration is unavailable. Try again later.');
      if (root.textContent?.includes('successfully')) throw new Error('A failed registration must not report success');
    } finally {
      stub.restore();
    }
  },
};
