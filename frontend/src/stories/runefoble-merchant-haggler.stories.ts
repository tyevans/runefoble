import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/minigames/runefoble-merchant-haggler.ts';

const meta: Meta = {
  title: 'Minigames/RunefobleMerchantHaggler',
  component: 'runefoble-merchant-haggler',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const ActiveNegotiationLight: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc);">
      <runefoble-merchant-haggler
        negotiation-id="neg-101"
        merchant-name="Torvin Ironbreaker"
        temperament="Stubborn"
        .patience=${4}
        .originalPrice=${100}
        .currentOffer=${70}
        .counterPrice=${85}
        item-name="Reinforced Kite Shield"
        last-voice-bark="Dwarven steel doesn't bend for pennies! Meet me at 85 gold, or keep walkin'!"
        .merchantMoodScore=${-5}
        status="active"
      ></runefoble-merchant-haggler>
    </div>
  `,
};

export const ActiveNegotiationDark: Story = {
  render: () => html`
    <div class="theme-dark-fantasy" style="padding: 24px; background: #09090b; min-height: 100vh;">
      <runefoble-merchant-haggler
        negotiation-id="neg-102"
        merchant-name="Torvin Ironbreaker"
        temperament="Greedy"
        .patience=${3}
        .originalPrice=${350}
        .currentOffer=${260}
        .counterPrice=${310}
        item-name="Folded Adamantine Blade"
        last-voice-bark="A recurring contract? Now that's music to my ears. I can shave the margin down."
        .merchantMoodScore=${8}
        status="active"
      ></runefoble-merchant-haggler>
    </div>
  `,
};

export const LowPatienceWarning: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc);">
      <runefoble-merchant-haggler
        negotiation-id="neg-103"
        merchant-name="Krag the Fence"
        temperament="Hostile"
        .patience=${1}
        .originalPrice=${200}
        .currentOffer=${100}
        .counterPrice=${190}
        item-name="Shadow Silk Cloak"
        last-voice-bark="One more insulting offer and my blade does the talking! Final price 190 GP."
        .merchantMoodScore=${-35}
        status="active"
      ></runefoble-merchant-haggler>
    </div>
  `,
};

export const CompletedTransaction: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc);">
      <runefoble-merchant-haggler
        negotiation-id="neg-104"
        merchant-name="Milo Goodbarrel"
        temperament="Generous"
        .patience=${5}
        .originalPrice=${50}
        .currentOffer=${35}
        .counterPrice=${35}
        item-name="Elixir of Heroism"
        last-voice-bark="Sold! A hard bargain well struck. Enjoy the draught, friend!"
        .merchantMoodScore=${25}
        status="completed"
      ></runefoble-merchant-haggler>
    </div>
  `,
};
