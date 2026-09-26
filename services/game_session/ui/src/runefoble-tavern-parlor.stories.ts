import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-tavern-parlor.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleTavernParlor',
  component: 'runefoble-tavern-parlor',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const LiarsDiceActiveRound: Story = {
  render: () => html`
    <runefoble-tavern-parlor
      session-id="session-tavern-01"
      campaign-id="campaign-whispering-isles"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      activeTab="dice"
      .wagerGold=${10}
      .diceRolls=${[2, 3, 3, 5, 6]}
      .currentBid=${{ quantity: 3, face: 4, bidder: 'npc_pirate' }}
    ></runefoble-tavern-parlor>
  `,
};

export const DrinkingContestIntoxicated: Story = {
  render: () => html`
    <runefoble-tavern-parlor
      session-id="session-tavern-02"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      activeTab="drinking"
      intoxicationLevel="drunk"
      .drinksConsumed=${4}
      .dspActive=${true}
    ></runefoble-tavern-parlor>
  `,
};

export const MerchantHagglingStubbornGreedy: Story = {
  render: () => html`
    <runefoble-tavern-parlor
      session-id="session-tavern-03"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      activeTab="merchant"
      merchantName="Thorin Stoneforged"
      merchantTemperament="stubborn_greedy"
      .basePrice=${50}
      .offeredPrice=${35}
      .lastCounterOffer=${42}
      lastVoiceBark="Dwarven steel doesn't bend for pennies! Meet me at 42 gold, or keep walkin'!"
    ></runefoble-tavern-parlor>
  `,
};

export const CardTournamentDuel: Story = {
  render: () => html`
    <runefoble-tavern-parlor
      session-id="session-tavern-04"
      character-id="char-bram"
      character-name="Bram the Tinkerer"
      activeTab="dice"
      .wagerGold=${25}
      .diceRolls=${[1, 1, 4, 6, 6]}
      .revealed=${true}
    ></runefoble-tavern-parlor>
  `,
};
