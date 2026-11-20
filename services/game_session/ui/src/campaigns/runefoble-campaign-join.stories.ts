import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-campaign-join.ts';
import type { CampaignJoinPhase } from './types.ts';

const meta: Meta = {
  title: 'GameSession/CampaignJoin',
  component: 'runefoble-campaign-join',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const STORY_TOKEN = 'story-invite-token-7f3a';

function joinView(phase: CampaignJoinPhase, extra: { message?: string; campaignId?: string; memberRole?: string } = {}) {
  return html`
    <runefoble-campaign-join
      invite-token=${STORY_TOKEN}
      .phase=${phase}
      .message=${extra.message ?? ''}
      campaign-id=${extra.campaignId ?? 'camp-story-1'}
      member-role=${extra.memberRole ?? 'player'}
    ></runefoble-campaign-join>
  `;
}

/** Signed out. The person enters a display name and an e-mail address. */
export const AccountForm: Story = { render: () => joinView('account-form') };

/** Signed out. The account request is running. */
export const AccountSending: Story = { render: () => joinView('account-sending') };

/** Signed out. The account request was refused. The form keeps the entered values. */
export const AccountRefused: Story = {
  render: () => joinView('account-refused', { message: 'This invite link has expired or has no uses left.' }),
};

/** Signed out. The account exists or is created. The person reads the Zitadel e-mail and signs in. */
export const AccountAccepted: Story = { render: () => joinView('account-accepted') };

/** Signed in. The person joins with the invite. */
export const JoinReady: Story = { render: () => joinView('join-ready') };

/** Signed in. The join request is running. */
export const Joining: Story = { render: () => joinView('joining') };

/** Signed in. The join succeeded. */
export const Joined: Story = { render: () => joinView('joined', { memberRole: 'player' }) };

/** Signed in. The server refused the join. The server message shows. */
export const JoinRefused: Story = {
  render: () => joinView('join-refused', { message: 'This invite link is not valid.' }),
};
