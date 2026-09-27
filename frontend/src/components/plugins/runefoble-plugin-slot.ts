/**
 * Runefoble Community Plugin UI Extension Slot Component
 * ADR-0004: Lit Web Components and Storybook UI
 * ADR-0012: Design System Theming and Bauhaus Modernism
 * TASK-0174: Community Plugin UI Extension Slots Microfrontend
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { pluginRegistry, type PluginDefinition, type PluginRegistryEvent, type SlotIdentifier } from './plugin_registry.ts';
import { sandboxStyles, instantiatePluginElement } from './plugin_sandbox.ts';

@customElement('runefoble-plugin-slot')
export class RunefoblePluginSlot extends LitElement {
  // Target slots: 'hud-widget', 'dice-panel', 'sidebar-tool'
  @property({ type: String, attribute: 'slot-name' }) slotName: SlotIdentifier = 'hud-widget';

  @property({ type: String, attribute: 'slot-id' })
  set slotId(val: SlotIdentifier) { this.slotName = val; }
  get slotId(): SlotIdentifier { return this.slotName; }

  @property({ type: String }) orientation: 'vertical' | 'horizontal' = 'vertical';
  @property({ type: Boolean, attribute: 'show-fallback' }) showFallback = true;
  @property({ type: String, attribute: 'fallback-text' }) fallbackText = '';

  @state() private activePlugins: PluginDefinition[] = [];
  private unsubscribe: (() => void) | null = null;

  static styles = [
    sandboxStyles,
    css`
      :host { display: block; box-sizing: border-box; }
      .slot-container { display: flex; gap: var(--rf-space-sm, 8px); width: 100%; box-sizing: border-box; }
      .slot-container.vertical { flex-direction: column; }
      .slot-container.horizontal { flex-direction: row; flex-wrap: wrap; }
      .slot-fallback {
        display: flex; align-items: center; justify-content: center;
        padding: var(--rf-space-md, 12px);
        border: var(--rf-border-width, 2px) dashed var(--rf-border-color, #1a202c);
        border-radius: var(--rf-border-radius, 4px);
        background: var(--rf-bg-surface, #ffffff);
        color: var(--rf-text-muted, #64748b);
        font-family: var(--rf-font-family, system-ui, sans-serif);
        font-size: var(--rf-font-size-sm, 0.85rem);
      }
      .plugin-host-wrapper {
        display: block;
        border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a202c);
        border-radius: var(--rf-border-radius, 4px);
        background: var(--rf-bg-surface, #ffffff);
        padding: var(--rf-space-sm, 8px);
        box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a202c);
      }
    `,
  ];

  connectedCallback() {
    super.connectedCallback();
    this.refreshPlugins();
    this.unsubscribe = pluginRegistry.subscribe((e: PluginRegistryEvent) => {
      if (e.type === 'cleared' || !e.slot || e.slot === this.slotName) this.refreshPlugins();
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has('slotName')) this.refreshPlugins();
    this.mountPlugins();
  }

  public refreshPlugins() {
    this.activePlugins = pluginRegistry.getPluginsForSlot(this.slotName);
  }

  private mountPlugins() {
    for (const p of this.activePlugins) {
      const container = this.shadowRoot?.querySelector<HTMLElement>(`#plugin-host-${p.id}`);
      if (container && container.children.length === 0) {
        const el = instantiatePluginElement(p, (err) => {
          this.dispatchEvent(new CustomEvent('plugin-error', { detail: { pluginId: p.id, error: err.message }, bubbles: true }));
        });
        if (el) {
          container.appendChild(el);
          this.dispatchEvent(new CustomEvent('plugin-mounted', { detail: { pluginId: p.id, slot: this.slotName }, bubbles: true }));
        }
      }
    }
  }

  render() {
    if (this.activePlugins.length === 0) {
      if (!this.showFallback) return html``;
      const text = this.fallbackText || `No plugins mounted for slot: ${this.slotName}`;
      return html`<slot name="fallback"><div class="slot-fallback">${text}</div></slot>`;
    }
    return html`
      <div class="slot-container ${this.orientation}">
        ${this.activePlugins.map((p) => html`
          <div class="plugin-sandbox-container plugin-host-wrapper" id="plugin-host-${p.id}" data-plugin-id="${p.id}"></div>
        `)}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-plugin-slot': RunefoblePluginSlot;
  }
}
