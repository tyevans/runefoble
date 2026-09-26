import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-spectator-overlay.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleSpectatorOverlay',
  component: 'runefoble-spectator-overlay',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultPartyHUD: Story = {
  render: () => html`
    <runefoble-spectator-overlay
      sessionId="camp-101-obs"
      position="bottom"
      transparent-mode
      .party=${[
        {
          id: 'p1',
          name: 'Valeros',
          hp: 45,
          maxHp: 45,
          color: '#3b82f6',
          conditions: ['Blessed'],
          isActiveTurn: false,
        },
        {
          id: 'p2',
          name: 'Kyra',
          hp: 28,
          maxHp: 32,
          color: '#db2777',
          conditions: ['Drunk (Missed Session)'],
          isAiControlled: true,
          isActiveTurn: false,
        },
        {
          id: 'p3',
          name: 'Merisiel',
          hp: 22,
          maxHp: 26,
          color: '#10b981',
          conditions: ['Stealth'],
          isActiveTurn: false,
        },
      ]}
      .camera=${{
        targetX: 3.5,
        targetY: 4.0,
        zoom: 1.5,
        durationMs: 300,
        easing: 'cubic-bezier(0.25, 0.1, 0.25, 1.0)',
      }}
    ></runefoble-spectator-overlay>
  `,
};

export const ActiveTurnFocus: Story = {
  render: () => html`
    <runefoble-spectator-overlay
      sessionId="camp-101-turn"
      position="bottom"
      transparent-mode
      .party=${[
        {
          id: 'p1',
          name: 'Valeros',
          hp: 45,
          maxHp: 45,
          color: '#3b82f6',
          conditions: ['Shield Up'],
          isActiveTurn: true,
        },
        {
          id: 'p2',
          name: 'Kyra',
          hp: 18,
          maxHp: 32,
          color: '#db2777',
          isAiControlled: true,
          conditions: ['Drunk'],
          isActiveTurn: false,
        },
      ]}
      .camera=${{
        targetX: 2.0,
        targetY: 3.0,
        zoom: 1.8,
        durationMs: 300,
        easing: 'cubic-bezier(0.25, 0.1, 0.25, 1.0)',
        activeTokenId: 'p1',
      }}
    ></runefoble-spectator-overlay>
  `,
};

export const CriticalRollAnimation: Story = {
  render: () => html`
    <runefoble-spectator-overlay
      sessionId="camp-101-crit"
      position="bottom"
      transparent-mode
      .party=${[
        {
          id: 'p1',
          name: 'Valeros',
          hp: 35,
          maxHp: 45,
          color: '#3b82f6',
          conditions: ['Blessed'],
          isActiveTurn: true,
        },
      ]}
      .activeRoll=${{
        rollerName: 'Valeros',
        diceFormula: '1d20 + 7 (Longsword Attack)',
        result: 27,
        isCritical: true,
      }}
    ></runefoble-spectator-overlay>
  `,
};

export const SidebarLayout: Story = {
  render: () => html`
    <runefoble-spectator-overlay
      sessionId="camp-101-sidebar"
      position="sidebar"
      transparent-mode
      .party=${[
        {
          id: 'p1',
          name: 'Valeros',
          hp: 12,
          maxHp: 45,
          color: '#3b82f6',
          conditions: ['Poisoned'],
          isActiveTurn: false,
        },
        {
          id: 'p2',
          name: 'Kyra',
          hp: 6,
          maxHp: 32,
          color: '#db2777',
          isAiControlled: true,
          conditions: ['Unconscious'],
          isActiveTurn: true,
        },
      ]}
    ></runefoble-spectator-overlay>
  `,
};
