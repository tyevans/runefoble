import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/plugins/runefoble-plugin-slot.ts';
import { pluginRegistry } from '../components/plugins/plugin_registry.ts';

if (typeof customElements !== 'undefined') {
  if (!customElements.get('mock-sidebar-tool')) {
    customElements.define('mock-sidebar-tool', class extends HTMLElement {
      connectedCallback() {
        this.innerHTML = '<div style="padding:6px; font-weight:700;">🧭 Hex Crawler Tool</div>';
      }
    });
  }
  if (!customElements.get('mock-hud-widget')) {
    customElements.define('mock-hud-widget', class extends HTMLElement {
      connectedCallback() {
        this.innerHTML = '<div style="padding:6px; font-weight:700; color:var(--rf-color-accent, #e63946);">⏳ Encounter Clock (Turn 3)</div>';
      }
    });
  }
  if (!customElements.get('mock-dice-panel')) {
    customElements.define('mock-dice-panel', class extends HTMLElement {
      connectedCallback() {
        this.innerHTML = '<div style="padding:6px; font-weight:700;">🎲 Wild Magic Surge Roller</div>';
      }
    });
  }
}

pluginRegistry.register({ id: 'mod-sidebar', name: 'Hex Crawler', slot: 'sidebar-tool', tag: 'mock-sidebar-tool' });
pluginRegistry.register({ id: 'mod-hud', name: 'Encounter Clock', slot: 'hud-widget', tag: 'mock-hud-widget' });
pluginRegistry.register({ id: 'mod-dice', name: 'Wild Magic', slot: 'dice-panel', tag: 'mock-dice-panel' });

const meta: Meta = {
  title: 'Plugins/RunefoblePluginSlot',
  component: 'runefoble-plugin-slot',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const renderSlotContainer = (theme: 'light' | 'dark', slotId: string, title: string) => html`
  <div data-theme="${theme}" style="background:var(--rf-bg-canvas, #f8f9fa); color:var(--rf-text-primary, #1a202c); padding:24px; font-family:var(--rf-font-family, sans-serif); max-width:440px; border:var(--rf-border-width, 2px) solid var(--rf-border-color, #1a202c); border-radius:var(--rf-border-radius, 4px);">
    <h4 style="margin:0 0 12px 0;">${title} (${theme.toUpperCase()})</h4>
    <runefoble-plugin-slot slot-id="${slotId}"></runefoble-plugin-slot>
  </div>
`;

export const SidebarToolLight: Story = {
  render: () => renderSlotContainer('light', 'sidebar-tool', 'Sidebar Extension Slot'),
};

export const SidebarToolDark: Story = {
  render: () => renderSlotContainer('dark', 'sidebar-tool', 'Sidebar Extension Slot'),
};

export const HudWidgetLight: Story = {
  render: () => renderSlotContainer('light', 'hud-widget', 'HUD Extension Slot'),
};

export const HudWidgetDark: Story = {
  render: () => renderSlotContainer('dark', 'hud-widget', 'HUD Extension Slot'),
};

export const DicePanelLight: Story = {
  render: () => renderSlotContainer('light', 'dice-panel', 'Dice Tray Extension Slot'),
};

export const DicePanelDark: Story = {
  render: () => renderSlotContainer('dark', 'dice-panel', 'Dice Tray Extension Slot'),
};

export const FallbackPlaceholder: Story = {
  render: () => html`
    <div style="background:var(--rf-bg-canvas, #f8f9fa); padding:24px; max-width:440px;">
      <runefoble-plugin-slot slot-id="unregistered-slot" fallback-text="No community plugins active in this slot"></runefoble-plugin-slot>
    </div>
  `,
};
