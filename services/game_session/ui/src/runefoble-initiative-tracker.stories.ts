import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-initiative-tracker.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleInitiativeTracker',
  component: 'runefoble-initiative-tracker',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ActiveCombat: Story = {
  render: () => html`
    <runefoble-initiative-tracker
      sessionId="session-ambush-101"
      .roundNumber=${1}
      .inCombat=${true}
      activeCombatantId="pc-valeros"
      .turnSecondsRemaining=${45}
      .turnTotalSeconds=${60}
      .combatants=${[
        {
          id: 'pc-valeros',
          name: 'Valeros (Fighter)',
          initiativeScore: 20,
          isNpc: false,
          armorClass: 18,
          hp: 38,
          maxHp: 44,
        },
        {
          id: 'npc-goblin-archer',
          name: 'Goblin Archer',
          initiativeScore: 15,
          isNpc: true,
          armorClass: 13,
          hp: 7,
          maxHp: 7,
        },
        {
          id: 'pc-kyra',
          name: 'Kyra (Cleric)',
          initiativeScore: 12,
          isNpc: false,
          armorClass: 16,
          hp: 26,
          maxHp: 32,
        },
      ]}
    ></runefoble-initiative-tracker>
  `,
};

export const UrgentTurnTimer: Story = {
  render: () => html`
    <runefoble-initiative-tracker
      sessionId="session-boss-fight"
      .roundNumber=${2}
      .inCombat=${true}
      activeCombatantId="pc-merisiel"
      .turnSecondsRemaining=${6}
      .turnTotalSeconds=${60}
      .combatants=${[
        {
          id: 'pc-merisiel',
          name: 'Merisiel (Rogue)',
          initiativeScore: 22,
          isNpc: false,
          armorClass: 17,
          hp: 14,
          maxHp: 28,
        },
        {
          id: 'npc-dragon',
          name: 'Young Red Dragon',
          initiativeScore: 18,
          isNpc: true,
          armorClass: 19,
          hp: 110,
          maxHp: 136,
        },
        {
          id: 'pc-ezren',
          name: 'Ezren (Wizard)',
          initiativeScore: 11,
          isNpc: false,
          armorClass: 12,
          hp: 18,
          maxHp: 18,
        },
      ]}
    ></runefoble-initiative-tracker>
  `,
};

export const EncounterLobby: Story = {
  render: () => html`
    <runefoble-initiative-tracker
      sessionId="session-lobby"
      .roundNumber=${1}
      .inCombat=${false}
      .combatants=${[]}
    ></runefoble-initiative-tracker>
  `,
};
