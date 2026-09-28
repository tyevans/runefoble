import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/dm-controls/runefoble-dm-negotiation-drawer.ts';

const meta: Meta = {
  title: 'DMControls/RunefobleDMNegotiationDrawer',
  component: 'runefoble-dm-negotiation-drawer',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const LiveArbitrationLight: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc);">
      <runefoble-dm-negotiation-drawer
        negotiation-id="neg-dm-01"
        merchant-name="Torvin Ironbreaker"
        character-name="Lady Nicole"
        item-name="Folded Adamantine Blade"
        .originalPrice=${350}
        .currentOffer=${260}
        .counterPrice=${300}
        .patience=${4}
        status="active"
      ></runefoble-dm-negotiation-drawer>
    </div>
  `,
};

export const LiveArbitrationDark: Story = {
  render: () => html`
    <div class="theme-dark-fantasy" style="padding: 24px; background: #09090b; min-height: 100vh;">
      <runefoble-dm-negotiation-drawer
        negotiation-id="neg-dm-02"
        merchant-name="Torvin Ironbreaker"
        character-name="Lady Nicole"
        item-name="Folded Adamantine Blade"
        .originalPrice=${350}
        .currentOffer=${280}
        .counterPrice=${280}
        .patience=${2}
        status="active"
      ></runefoble-dm-negotiation-drawer>
    </div>
  `,
};

export const DealCompletedDrawer: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc);">
      <runefoble-dm-negotiation-drawer
        negotiation-id="neg-dm-03"
        merchant-name="Torvin Ironbreaker"
        character-name="Lady Nicole"
        item-name="Folded Adamantine Blade"
        .originalPrice=${350}
        .currentOffer=${280}
        .counterPrice=${280}
        .patience=${5}
        status="completed"
      ></runefoble-dm-negotiation-drawer>
    </div>
  `,
};
