import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-breadcrumbs.ts';

const meta: Meta = {
  title: 'Shell/RunefobleBreadcrumbs',
  component: 'runefoble-breadcrumbs',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const CampaignDashboard: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-breadcrumbs
        .items=${[{ label: 'Campaigns', path: '#/campaigns', active: true }]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};

export const CampaignDetails: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-breadcrumbs
        .items=${[
          { label: 'Campaigns', path: '#/campaigns' },
          { label: 'Tomb of the Star-Eater', path: '#/campaigns/4', active: true },
        ]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};

export const PreGameLobby: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-breadcrumbs
        .items=${[
          { label: 'Campaigns', path: '#/campaigns' },
          { label: 'Tomb of the Star-Eater', path: '#/campaigns/4' },
          { label: 'Lobby 15', path: '#/campaigns/4/lobby/15', active: true },
        ]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};

export const ActiveSession: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-breadcrumbs
        .items=${[
          { label: 'Campaigns', path: '#/campaigns' },
          { label: 'Tomb of the Star-Eater', path: '#/campaigns/4' },
          { label: 'Session #14', path: '#/campaigns/4/sessions/14', active: true },
        ]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};

export const DarkModeActiveSession: Story = {
  render: () => html`
    <div
      data-theme="bauhaus"
      data-color-mode="dark"
      style="padding: 24px; background: var(--rf-bg-canvas, #121820); color: var(--rf-text-primary, #f1f5f9);"
    >
      <runefoble-breadcrumbs
        .items=${[
          { label: 'Campaigns', path: '#/campaigns' },
          { label: 'Tomb of the Star-Eater', path: '#/campaigns/4' },
          { label: 'Session #14', path: '#/campaigns/4/sessions/14', active: true },
        ]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};

export const CustomSlashSeparator: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-breadcrumbs
        separator="/"
        .items=${[
          { label: 'Campaigns', path: '#/campaigns' },
          { label: 'Tomb of the Star-Eater', path: '#/campaigns/4' },
          { label: 'Characters', path: '#/campaigns/4/characters', active: true },
        ]}
      ></runefoble-breadcrumbs>
    </div>
  `,
};
