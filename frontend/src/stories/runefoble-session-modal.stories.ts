/**
 * Storybook stories for Runefoble Session Modal Component
 * TASK-0249: Session Scheduling and Staging Lobby Creation Modal
 * Governed by ADR-0004, ADR-0012.
 */

import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-session-modal.ts';

const meta: Meta = {
  title: 'Campaign/RunefobleSessionModal',
  component: 'runefoble-session-modal',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultOpenLobby: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
        initialStatus="lobby"
      ></runefoble-session-modal>
    </div>
  `,
};

export const OpenUpcomingSession: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
        initialStatus="upcoming"
      ></runefoble-session-modal>
    </div>
  `,
};

export const ModalWithValidationError: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
        errorMessage="Session title is required"
      ></runefoble-session-modal>
    </div>
  `,
};

export const DarkMode: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="bauhaus"
      style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #121212);"
    >
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
      ></runefoble-session-modal>
    </div>
  `,
};

export const LightMode: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="bauhaus"
      style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #f8f9fa);"
    >
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
      ></runefoble-session-modal>
    </div>
  `,
};

export const CyberRuneTheme: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="cyber-rune"
      style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #09090b);"
    >
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
      ></runefoble-session-modal>
    </div>
  `,
};

export const ParchmentTheme: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="parchment"
      style="padding: 24px; min-height: 520px; background: var(--rf-bg-canvas, #f4ecd8);"
    >
      <runefoble-session-modal
        .open=${true}
        campaign-id="4"
      ></runefoble-session-modal>
    </div>
  `,
};
