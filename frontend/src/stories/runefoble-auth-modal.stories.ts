/**
 * Storybook stories for Runefoble Zitadel Authentication Components
 * ADR-0004, ADR-0012, ADR-0013, TASK-0207
 */

import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-auth-modal.ts';
import '../components/runefoble-user-menu.ts';
import type { UserClaims } from '../auth/auth-service.ts';

const meta: Meta = {
  title: 'Auth/RunefobleAuthModal',
  component: 'runefoble-auth-modal',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleUser: UserClaims = {
  user_id: 'user-valeros-01',
  username: 'Valeros',
  email: 'valeros@runefoble.local',
  roles: ['player', 'dm', 'admin'],
  is_admin: true,
};

export const UnauthenticatedSignInModal: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 480px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-auth-modal .open=${true} initialTab="login"></runefoble-auth-modal>
    </div>
  `,
};

export const SignUpModal: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 480px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-auth-modal .open=${true} initialTab="register"></runefoble-auth-modal>
    </div>
  `,
};

export const ModalWithValidationError: Story = {
  render: () => html`
    <div style="padding: 24px; min-height: 480px; background: var(--rf-bg-canvas, #f8f9fa);">
      <runefoble-auth-modal
        .open=${true}
        initialTab="register"
        errorMessage="Passwords do not match"
      ></runefoble-auth-modal>
    </div>
  `,
};

export const AuthenticatedUserMenuLight: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="bauhaus"
      style="padding: 40px; background: var(--rf-bg-canvas, #f8f9fa); display: flex; justify-content: flex-end;"
    >
      <runefoble-user-menu .user=${sampleUser}></runefoble-user-menu>
    </div>
  `,
};

export const AuthenticatedUserMenuDark: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="bauhaus"
      style="padding: 40px; background: var(--rf-bg-canvas, #121212); display: flex; justify-content: flex-end;"
    >
      <runefoble-user-menu .user=${sampleUser}></runefoble-user-menu>
    </div>
  `,
};

export const UserMenuParchmentTheme: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="parchment"
      style="padding: 40px; background: var(--rf-bg-canvas, #f4ecd8); display: flex; justify-content: flex-end;"
    >
      <runefoble-user-menu .user=${sampleUser}></runefoble-user-menu>
    </div>
  `,
};

export const UserMenuCyberRuneTheme: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="cyber-rune"
      style="padding: 40px; background: var(--rf-bg-canvas, #09090b); display: flex; justify-content: flex-end;"
    >
      <runefoble-user-menu .user=${sampleUser}></runefoble-user-menu>
    </div>
  `,
};

export const UnauthenticatedSignInButton: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8f9fa); display: flex; justify-content: flex-end;">
      <runefoble-user-menu .user=${null}></runefoble-user-menu>
    </div>
  `,
};
