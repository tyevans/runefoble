import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './radial_menu.ts';
import { RADIAL_ACTIONS } from './radial/radial_wedge.ts';

const meta: Meta = {
  title: 'BoardState/RadialMenu',
  component: 'runefoble-radial-menu',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultRadialMenu: Story = {
  render: () => html`
    <div style="position: relative; width: 300px; height: 300px; margin: 60px auto; display: flex; align-items: center; justify-content: center;">
      <runefoble-radial-menu
        .tokenId=${'hero-1'}
        .tokenName=${'Valeros'}
        .radius=${68}
        .actions=${RADIAL_ACTIONS}
        @action-select=${(e: CustomEvent) => console.log('Action selected:', e.detail)}
        @menu-close=${(e: CustomEvent) => console.log('Menu closed:', e.detail)}
      ></runefoble-radial-menu>
    </div>
  `,
};

export const ExpandedRadius: Story = {
  render: () => html`
    <div style="position: relative; width: 360px; height: 360px; margin: 80px auto; display: flex; align-items: center; justify-content: center;">
      <runefoble-radial-menu
        .tokenId=${'rogue-1'}
        .tokenName=${'Merisiel'}
        .radius=${92}
        .actions=${RADIAL_ACTIONS}
      ></runefoble-radial-menu>
    </div>
  `,
};

export const CustomActionsPalette: Story = {
  render: () => {
    const customActions = [
      ...RADIAL_ACTIONS,
      {
        id: 'shove' as const,
        label: 'Shove',
        icon: 'attack',
        color: '#e76f51',
        description: 'Push target 5ft back or knock prone',
      },
    ];
    return html`
      <div style="position: relative; width: 320px; height: 320px; margin: 70px auto; display: flex; align-items: center; justify-content: center;">
        <runefoble-radial-menu
          .tokenId=${'fighter-1'}
          .tokenName=${'Amiri'}
          .radius=${75}
          .actions=${customActions}
        ></runefoble-radial-menu>
      </div>
    `;
  },
};
