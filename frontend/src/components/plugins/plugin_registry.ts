/**
 * Runefoble Community Plugin Registry & Lifecycle Manager
 * ADR-0004: Lit Web Components and Storybook UI
 * ADR-0013: Microfrontend Architecture and Service Component Vendoring
 * TASK-0174: Community Plugin UI Extension Slots Microfrontend
 */

export type SlotIdentifier = 'hud-widget' | 'dice-panel' | 'sidebar-tool' | string;

export interface PluginDefinition {
  id: string;
  name: string;
  slot: SlotIdentifier;
  tag: string;
  version?: string;
  author?: string;
  order?: number;
  props?: Record<string, unknown>;
  enabled?: boolean;
}

export type PluginRegistryEventType = 'registered' | 'unregistered' | 'cleared';

export interface PluginRegistryEvent {
  type: PluginRegistryEventType;
  plugin?: PluginDefinition;
  slot?: string;
}

export type PluginRegistryListener = (event: PluginRegistryEvent) => void;

export class PluginRegistry {
  private plugins = new Map<string, PluginDefinition>();
  private listeners = new Set<PluginRegistryListener>();

  public register(plugin: PluginDefinition): void {
    if (!plugin.id || !plugin.slot || !plugin.tag) {
      throw new Error(`Invalid plugin definition: missing id, slot, or tag`);
    }
    const def: PluginDefinition = {
      ...plugin,
      enabled: plugin.enabled ?? true,
      order: plugin.order ?? 0,
    };
    this.plugins.set(def.id, def);
    this.notify({ type: 'registered', plugin: def, slot: def.slot });
  }

  public unregister(id: string): boolean {
    const plugin = this.plugins.get(id);
    if (!plugin) return false;
    this.plugins.delete(id);
    this.notify({ type: 'unregistered', plugin, slot: plugin.slot });
    return true;
  }

  public getPlugin(id: string): PluginDefinition | undefined {
    return this.plugins.get(id);
  }

  public getPluginsForSlot(slot: string): PluginDefinition[] {
    return Array.from(this.plugins.values())
      .filter((p) => p.slot === slot && p.enabled !== false)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  }

  public getAllPlugins(): PluginDefinition[] {
    return Array.from(this.plugins.values());
  }

  public clear(): void {
    this.plugins.clear();
    this.notify({ type: 'cleared' });
  }

  public subscribe(listener: PluginRegistryListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(event: PluginRegistryEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch (err) {
        console.error('Plugin registry listener error:', err);
      }
    }
  }
}

export const pluginRegistry = new PluginRegistry();

export function registerDefaultPlugins(reg: PluginRegistry = pluginRegistry, isDm = false): void {
  const base: PluginDefinition[] = [
    { id: 'default-initiative-tracker', name: 'Initiative Tracker', slot: 'hud-widget', tag: 'runefoble-initiative-tracker', order: 10 },
    { id: 'default-soundscape-controls', name: 'Soundscape Controls', slot: 'hud-widget', tag: 'runefoble-soundscape-controls', order: 20 },
    { id: 'default-dice-roller', name: 'Dice Roller', slot: 'dice-panel', tag: 'runefoble-dice-roller', order: 10 },
    { id: 'default-dice-tray-3d', name: '3D Dice Tray', slot: 'dice-panel', tag: 'runefoble-dice-tray-3d', order: 20 },
    { id: 'default-combat-reaction-prompt', name: 'Combat Reaction Prompt', slot: 'sidebar-tool', tag: 'runefoble-combat-reaction-prompt', order: 10 },
  ];
  for (const p of base) if (!reg.getPlugin(p.id)) reg.register(p);
  const dm: PluginDefinition[] = [
    { id: 'default-dm-whisper-bar', name: 'DM Whisper Bar', slot: 'sidebar-tool', tag: 'runefoble-dm-whisper-bar', order: 20 },
    { id: 'default-dm-trap-controls', name: 'DM Trap Controls', slot: 'sidebar-tool', tag: 'runefoble-dm-trap-controls', order: 30 },
  ];
  for (const p of dm) {
    if (isDm) { if (!reg.getPlugin(p.id)) reg.register(p); }
    else if (reg.getPlugin(p.id)) reg.unregister(p.id);
  }
}

registerDefaultPlugins(pluginRegistry, false);
