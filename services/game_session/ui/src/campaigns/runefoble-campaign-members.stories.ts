import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-members.ts';
import type { CampaignMember } from './types.ts';

const meta: Meta = {
  title: 'GameSession/CampaignMembers',
  component: 'runefoble-campaign-members',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleMembers: CampaignMember[] = [
  {
    user_id: 'usr-evelyn',
    username: 'Evelyn (You)',
    character_name: 'Dungeon Master',
    role: 'owner',
  },
  {
    user_id: 'usr-marcus',
    username: 'Marcus Vance',
    character_name: 'Thorin Stonehelm (Dwarf Paladin)',
    role: 'player',
  },
  {
    user_id: 'usr-lyra',
    username: 'Lyra Moonshadow',
    character_name: 'Aeloria (Elf Wizard)',
    role: 'player',
  },
  {
    user_id: 'usr-garrick',
    username: 'Garrick Bronzearm',
    character_name: 'Assistant DM / Stand-in',
    role: 'dungeon_master',
  },
  {
    user_id: 'usr-spectator-tom',
    username: 'Spectator Tom',
    role: 'spectator',
  },
];

export const GmManagementMode: Story = {
  render: () => html`
    <runefoble-campaign-members
      campaign-id="camp-drakkenheim-001"
      campaign-title="Shadows of Drakkenheim"
      current-user-id="usr-evelyn"
      .canManage=${true}
      .members=${sampleMembers}
      invite-token="sample_invite_token_xyz"
    ></runefoble-campaign-members>
  `,
};

export const PlayerViewOnlyMode: Story = {
  render: () => html`
    <runefoble-campaign-members
      campaign-id="camp-drakkenheim-001"
      campaign-title="Shadows of Drakkenheim"
      current-user-id="usr-marcus"
      .canManage=${false}
      .members=${sampleMembers}
    ></runefoble-campaign-members>
  `,
};

export const EmptyRoster: Story = {
  render: () => html`
    <runefoble-campaign-members
      campaign-id="camp-new-002"
      campaign-title="Frontier Caravan Run"
      current-user-id="usr-evelyn"
      .canManage=${true}
      .members=${[]}
    ></runefoble-campaign-members>
  `,
};

export const CustomInviteLink: Story = {
  render: () => html`
    <runefoble-campaign-members
      campaign-id="camp-curse-strahd"
      campaign-title="Curse of Strahd: Reloaded"
      current-user-id="usr-evelyn"
      .canManage=${true}
      .members=${sampleMembers}
      invite-url="https://app.runefoble.com/#/join/invite-custom-token-99"
    ></runefoble-campaign-members>
  `,
};
