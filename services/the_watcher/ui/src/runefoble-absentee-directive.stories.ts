import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-absentee-directive.ts';
import type { DecisionPoll } from './runefoble-absentee-vote-card.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleAbsenteeDirective',
  component: 'runefoble-absentee-directive',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleRestPoll: DecisionPoll = {
  id: 'poll-rest-101',
  title: 'Long Rest at Sunken Grotto?',
  description: 'Party depleted spell slots and hit dice. Risk 8 hours in damp cavern?',
  expiresInSeconds: 45,
  options: [
    { id: 'opt-long-rest', label: 'Take Long Rest (Full Recovery)', votes: 2 },
    { id: 'opt-short-rest', label: 'Short Rest & Press Forward', votes: 1 },
    { id: 'opt-scout-first', label: 'Scout Perimeter Before Resting', votes: 0 },
  ],
};

export const Default: Story = {
  render: () => html`
    <runefoble-absentee-directive
      characterName="Sarah"
      characterClass="Life Domain Cleric (Lvl 5)"
      .standInActive=${true}
      currentStance="defensive"
      .currentHp=${28}
      .maxHp=${38}
      .penalties=${['drunk', 'foolishness']}
      .activePoll=${sampleRestPoll}
    ></runefoble-absentee-directive>
  `,
};

export const CautiousHeroic: Story = {
  render: () => html`
    <runefoble-absentee-directive
      characterName="Marcus"
      characterClass="Battle Master Fighter (Lvl 5)"
      .standInActive=${true}
      currentStance="cautious"
      .currentHp=${45}
      .maxHp=${52}
      .penalties=${['greed']}
      .activePoll=${sampleRestPoll}
    ></runefoble-absentee-directive>
  `,
};

export const AggressivePosture: Story = {
  render: () => html`
    <runefoble-absentee-directive
      characterName="Evelyn"
      characterClass="Evocation Wizard (Lvl 6)"
      .standInActive=${true}
      currentStance="heroic"
      .currentHp=${18}
      .maxHp=${32}
      .penalties=${['foolishness']}
    ></runefoble-absentee-directive>
  `,
};

export const WithoutActivePoll: Story = {
  render: () => html`
    <runefoble-absentee-directive
      characterName="Sarah"
      characterClass="Life Domain Cleric (Lvl 5)"
      .standInActive=${true}
      currentStance="defensive"
      .currentHp=${38}
      .maxHp=${38}
      .penalties=${[]}
    ></runefoble-absentee-directive>
  `,
};

export const LightThemePreview: Story = {
  render: () => html`
    <div style="background: #ffffff; color: #1e293b; padding: 16px; border-radius: 8px;">
      <runefoble-absentee-directive
        characterName="Sarah"
        characterClass="Cleric"
        .standInActive=${true}
        currentStance="defensive"
        .currentHp=${30}
        .maxHp=${38}
        .penalties=${['drunk']}
        .activePoll=${sampleRestPoll}
        style="--rf-bg-surface: #f8fafc; --rf-bg-surface-raised: #f1f5f9; --rf-border-color: #cbd5e1; --rf-text-primary: #0f172a; --rf-text-secondary: #475569;"
      ></runefoble-absentee-directive>
    </div>
  `,
};
