import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-user-profile.ts';

const meta: Meta = {
  title: 'Profile/RunefobleUserProfile',
  component: 'runefoble-user-profile',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultPlayerProfile: Story = {
  render: () => html`
    <div style="padding: 32px; background: var(--rf-bg-canvas, #f8f9fa); min-height: 100vh;">
      <runefoble-user-profile
        .user=${{
          user_id: 'user-valeros',
          username: 'Valeros of Korvosa',
          email: 'valeros@runefoble.local',
          roles: ['player'],
          is_admin: false,
        }}
        currentTheme="bauhaus"
        currentColorMode="light"
      ></runefoble-user-profile>
    </div>
  `,
};

export const AdminDungeonMasterProfile: Story = {
  render: () => html`
    <div style="padding: 32px; background: var(--rf-bg-canvas, #f8f9fa); min-height: 100vh;">
      <runefoble-user-profile
        .user=${{
          user_id: 'user-watcher-admin',
          username: 'The Watcher',
          email: 'admin@runefoble.local',
          roles: ['dm', 'admin', 'owner'],
          is_admin: true,
        }}
        currentTheme="dark-fantasy"
        currentColorMode="dark"
      ></runefoble-user-profile>
    </div>
  `,
};

export const CyberRuneProfile: Story = {
  render: () => html`
    <div style="padding: 32px; background: var(--rf-bg-canvas, #f8f9fa); min-height: 100vh;" data-theme="cyber-rune">
      <runefoble-user-profile
        .user=${{
          user_id: 'user-merisiel',
          username: 'Merisiel Rogue',
          email: 'merisiel@runefoble.local',
          roles: ['player'],
          is_admin: false,
        }}
        currentTheme="cyber-rune"
        currentColorMode="dark"
      ></runefoble-user-profile>
    </div>
  `,
};
