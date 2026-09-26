import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-settings-modal.ts';

const meta: Meta = {
  title: 'Settings/RunefobleSettingsModal',
  component: 'runefoble-settings-modal',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const DefaultClosedTrigger: Story = {
  render: () => {
    let isOpen = false;
    const toggle = (e: Event) => {
      const target = e.currentTarget as HTMLElement;
      const modal = target.parentElement?.querySelector('runefoble-settings-modal') as any;
      if (modal) {
        isOpen = !isOpen;
        modal.open = isOpen;
      }
    };
    return html`
      <div
        style="
          padding: 24px;
          background: var(--rf-bg-canvas, #f8f9fa);
          border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
          display: flex;
          align-items: center;
          justify-content: space-between;
          max-width: 600px;
        "
      >
        <span style="font-weight: 800; font-family: var(--rf-font-family);">Runefoble Header Simulation</span>
        <button
          class="settings-trigger"
          aria-haspopup="dialog"
          aria-expanded="false"
          aria-label="Open settings"
          style="
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--rf-bg-surface, #ffffff);
            color: var(--rf-text-primary, #121212);
            border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
            box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
            font-weight: 700;
            font-size: 0.8rem;
            padding: 6px 12px;
            cursor: pointer;
          "
          @click=${toggle}
        >
          <span aria-hidden="true">⚙️</span>
          <span>Settings</span>
        </button>
        <runefoble-settings-modal></runefoble-settings-modal>
      </div>
    `;
  },
};

export const OpenLightMode: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="bauhaus"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #f8f9fa);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="light"
        currentTheme="bauhaus"
      ></runefoble-settings-modal>
    </div>
  `,
};

export const OpenDarkMode: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="bauhaus"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #121212);
        color: var(--rf-text-primary, #f8f9fa);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="dark"
        currentTheme="bauhaus"
      ></runefoble-settings-modal>
    </div>
  `,
};

export const OpenSystemMode: Story = {
  render: () => html`
    <div
      data-color-mode="system"
      data-theme="bauhaus"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #f8f9fa);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="system"
        currentTheme="bauhaus"
      ></runefoble-settings-modal>
    </div>
  `,
};

export const ActiveThemeCyberRune: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="cyber-rune"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #09090b);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="dark"
        currentTheme="cyber-rune"
      ></runefoble-settings-modal>
    </div>
  `,
};

export const ActiveThemeDarkFantasy: Story = {
  render: () => html`
    <div
      data-color-mode="dark"
      data-theme="dark-fantasy"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #0f172a);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="dark"
        currentTheme="dark-fantasy"
      ></runefoble-settings-modal>
    </div>
  `,
};

export const ActiveThemeParchment: Story = {
  render: () => html`
    <div
      data-color-mode="light"
      data-theme="parchment"
      style="
        min-height: 480px;
        padding: 24px;
        background: var(--rf-bg-canvas, #f4ecd8);
      "
    >
      <runefoble-settings-modal
        .open=${true}
        currentColorMode="light"
        currentTheme="parchment"
      ></runefoble-settings-modal>
    </div>
  `,
};
