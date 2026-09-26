import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-audience-studio.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleAudienceStudio',
  component: 'runefoble-audience-studio',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const samplePoll = {
  id: 'poll-1',
  title: 'Wild Magic Surge Target',
  prompt: 'Choose which creature is hit by the chaotic surge!',
  options: [
    { id: 'opt_1', label: 'Gorgon Boss (+5 Armor)', votes: 42 },
    { id: 'opt_2', label: 'Rogue Ally (Invisibility)', votes: 85 },
    { id: 'opt_3', label: 'Room Floor (Slick Ice)', votes: 19 },
  ],
  totalVotes: 146,
  quorum: 20,
  status: 'active',
};

const sampleProposals = [
  {
    id: 'prop-1',
    title: 'Wild Magic Surge: Rogue Ally',
    description: 'Audience voted for: Rogue Ally (Invisibility) (85/146 votes)',
    modifierType: 'chaos_modifier',
    status: 'pending',
  },
];

export const SpectatorVoting: Story = {
  render: () => html`
    <runefoble-audience-studio
      campaignId="campaign-alpha"
      sessionId="session-beta"
      userId="spectator-bob"
      .isDM=${false}
      .wsConnected=${true}
      .activePoll=${samplePoll}
    ></runefoble-audience-studio>
  `,
};

export const DungeonMasterApprovalQueue: Story = {
  render: () => html`
    <runefoble-audience-studio
      campaignId="campaign-alpha"
      sessionId="session-beta"
      userId="dm-alice"
      .isDM=${true}
      .wsConnected=${true}
      .activePoll=${samplePoll}
      .proposals=${sampleProposals}
    ></runefoble-audience-studio>
  `,
};

export const IdleNoActivePoll: Story = {
  render: () => html`
    <runefoble-audience-studio
      campaignId="campaign-alpha"
      sessionId="session-beta"
      userId="spectator-bob"
      .isDM=${false}
      .wsConnected=${false}
      .activePoll=${null}
    ></runefoble-audience-studio>
  `,
};
