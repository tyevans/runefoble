/**
 * Runefoble Shadow DOM Sandbox & CSS Custom Property Bridge
 * ADR-0004: Lit Web Components and Storybook UI
 * ADR-0012: Design System Theming and Bauhaus Modernism
 * TASK-0174: Community Plugin UI Extension Slots Microfrontend
 */

import { css } from 'lit';
import type { PluginDefinition } from './plugin_registry.ts';

export const ALLOWED_TOKEN_PREFIXES = [
  '--rf-color-',
  '--rf-space-',
  '--rf-font-',
  '--rf-border-',
  '--rf-shadow-',
  '--rf-bg-',
  '--rf-text-',
] as const;

export function isAllowedDesignToken(property: string): boolean {
  return ALLOWED_TOKEN_PREFIXES.some((prefix) => property.startsWith(prefix));
}

export const sandboxStyles = css`
  .plugin-sandbox-container {
    display: block;
    contain: layout style;
    isolation: isolate;
    position: relative;
    max-width: 100%;
    box-sizing: border-box;
  }
`;

export interface SandboxedEventDetail<T = unknown> {
  pluginId: string;
  slot: string;
  sourceTag: string;
  payload: T;
}

export function createSandboxedEvent<T>(
  plugin: PluginDefinition,
  eventName: string,
  payload: T,
  options?: { bubbles?: boolean; composed?: boolean }
): CustomEvent<SandboxedEventDetail<T>> {
  return new CustomEvent<SandboxedEventDetail<T>>(eventName, {
    bubbles: options?.bubbles ?? true,
    composed: options?.composed ?? false,
    detail: {
      pluginId: plugin.id,
      slot: plugin.slot,
      sourceTag: plugin.tag,
      payload,
    },
  });
}

export function instantiatePluginElement(
  plugin: PluginDefinition,
  onError?: (err: Error) => void
): HTMLElement | null {
  if (typeof document === 'undefined') return null;
  try {
    const el = document.createElement(plugin.tag);
    el.setAttribute('data-plugin-id', plugin.id);
    el.setAttribute('data-plugin-slot', plugin.slot);
    if (plugin.props) {
      for (const [key, val] of Object.entries(plugin.props)) {
        if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
          el.setAttribute(key, String(val));
        }
        (el as unknown as Record<string, unknown>)[key] = val;
      }
    }
    return el;
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error(String(err)));
    return null;
  }
}
