import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-session-list.ts';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';

const meta: Meta = {
  title: 'Shell/RunefobleSessionList',
  component: 'runefoble-session-list',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleSessions: CampaignSessionItem[] = [
  {
    id: 'session-tomb-14',
    campaignId: '4',
    title: 'Session #14: Tomb of the Star-Eater',
    status: 'active',
    round: 3,
    participantsCount: 4,
  },
  {
    id: 'session-lobby-15',
    campaignId: '4',
    title: 'Session #15: Chamber of Horrors',
    status: 'lobby',
    participantsCount: 3,
  },
  {
    id: 'session-16',
    campaignId: '4',
    title: 'Session #16: Astral Confrontation',
    status: 'upcoming',
    participantsCount: 0,
  },
];

export const WithActiveSessions: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa); max-width: 800px;">
      <runefoble-session-list
        campaign-id="4"
        .sessions=${sampleSessions}
        .isDm=${true}
      ></runefoble-session-list>
    </div>
  `,
};

export const EmptyState: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa); max-width: 800px;">
      <runefoble-session-list
        campaign-id="5"
        .sessions=${[]}
        .isDm=${true}
      ></runefoble-session-list>
    </div>
  `,
};
