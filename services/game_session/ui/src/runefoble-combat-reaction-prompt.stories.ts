import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-combat-reaction-prompt.ts';
import './runefoble-ready-action-card.ts';

const meta: Meta = {
  title: 'TTRPG/CombatReactionPrompt',
  component: 'runefoble-combat-reaction-prompt',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ActiveCountdown: Story = {
  render: () => html`
    <runefoble-combat-reaction-prompt
      sessionId="session-ambush-101"
      reactionId="rx-shield-001"
      reactingCombatantId="char-marcus"
      reactingCombatantName="Marcus (Abjurer)"
      triggerPhrase="I cast Shield!"
      reactionType="shield"
      .timeoutSeconds=${15}
      .secondsRemaining=${12}
    ></runefoble-combat-reaction-prompt>
  `,
};

export const UrgentExpiring: Story = {
  render: () => html`
    <runefoble-combat-reaction-prompt
      sessionId="session-boss-fight"
      reactionId="rx-counter-002"
      reactingCombatantId="char-ezren"
      reactingCombatantName="Ezren (Wizard)"
      triggerPhrase="Counterspell that!"
      reactionType="counterspell"
      .timeoutSeconds=${15}
      .secondsRemaining=${3}
    ></runefoble-combat-reaction-prompt>
  `,
};

export const TriggerAccepted: Story = {
  render: () => html`
    <runefoble-combat-reaction-prompt
      sessionId="session-dragon-lair"
      reactionId="rx-shield-003"
      reactingCombatantId="char-marcus"
      reactingCombatantName="Marcus (Abjurer)"
      triggerPhrase="I cast Shield!"
      reactionType="shield"
      status="resolved"
      resolvedAction="Cast Shield (+5 AC)"
    ></runefoble-combat-reaction-prompt>
  `,
};

export const TimeoutExpired: Story = {
  render: () => html`
    <runefoble-combat-reaction-prompt
      sessionId="session-dungeon-crawl"
      reactionId="rx-oa-004"
      reactingCombatantId="char-valeros"
      reactingCombatantName="Valeros (Fighter)"
      triggerPhrase="Opportunity Attack"
      reactionType="opportunity_attack"
      status="expired"
    ></runefoble-combat-reaction-prompt>
  `,
};

export const ReadyActionCardUnarmed: Story = {
  render: () => html`
    <runefoble-ready-action-card
      sessionId="session-ambush-101"
      combatantId="char-merisiel"
      combatantName="Merisiel (Rogue)"
      triggerCondition="if the goblin steps into the hallway"
      readiedAction="Shoot Heavy Crossbow"
      .rangeCells=${6}
    ></runefoble-ready-action-card>
  `,
};

export const ReadyActionCardArmed: Story = {
  render: () => html`
    <runefoble-ready-action-card
      sessionId="session-ambush-101"
      combatantId="char-merisiel"
      combatantName="Merisiel (Rogue)"
      triggerCondition="if the goblin steps into the hallway"
      readiedAction="Shoot Heavy Crossbow"
      .rangeCells=${6}
      .isArmed=${true}
    ></runefoble-ready-action-card>
  `,
};
