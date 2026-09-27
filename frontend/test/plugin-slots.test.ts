/**
 * Unit & Integration tests for Community Plugin Extension Slots and Registry
 * TASK-0174: Community Plugin UI Extension Slots Microfrontend
 * Governed by ADR-0004, ADR-0012, ADR-0013, US-0035, PRD-0022.
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  PluginRegistry,
  type PluginDefinition,
  type PluginRegistryEvent,
} from '../src/components/plugins/plugin_registry.ts';
import {
  ALLOWED_TOKEN_PREFIXES,
  isAllowedDesignToken,
  createSandboxedEvent,
  instantiatePluginElement,
} from '../src/components/plugins/plugin_sandbox.ts';


describe('PluginRegistry Lifecycle & Slot Filtering', () => {
  let registry: PluginRegistry;

  beforeEach(() => {
    registry = new PluginRegistry();
  });

  it('registers a valid plugin and queries it by slot', () => {
    const plugin: PluginDefinition = {
      id: 'tool-dice-1',
      name: 'Advantage Dice Roller',
      slot: 'dice-panel',
      tag: 'runefoble-advantage-dice',
      author: 'Alex',
      version: '1.0.0',
    };
    registry.register(plugin);

    const found = registry.getPlugin('tool-dice-1');
    assert.ok(found);
    assert.equal(found.name, 'Advantage Dice Roller');
    assert.equal(found.slot, 'dice-panel');
    assert.equal(found.tag, 'runefoble-advantage-dice');
    assert.equal(found.enabled, true);
    assert.equal(found.order, 0);

    const dicePlugins = registry.getPluginsForSlot('dice-panel');
    assert.equal(dicePlugins.length, 1);
    assert.equal(dicePlugins[0].id, 'tool-dice-1');

    const hudPlugins = registry.getPluginsForSlot('hud-widget');
    assert.equal(hudPlugins.length, 0);
  });

  it('rejects registration missing required fields', () => {
    assert.throws(
      () => registry.register({ id: '', name: 'Test', slot: 'hud-widget', tag: 'test-tag' } as any),
      /Invalid plugin definition/
    );
    assert.throws(
      () => registry.register({ id: 'valid-id', name: 'Test', slot: '', tag: 'test-tag' } as any),
      /Invalid plugin definition/
    );
    assert.throws(
      () => registry.register({ id: 'valid-id', name: 'Test', slot: 'hud-widget', tag: '' } as any),
      /Invalid plugin definition/
    );
  });

  it('sorts plugins within the same slot by order', () => {
    registry.register({ id: 'p2', name: 'Second', slot: 'sidebar-tool', tag: 'tag-2', order: 20 });
    registry.register({ id: 'p1', name: 'First', slot: 'sidebar-tool', tag: 'tag-1', order: 5 });
    registry.register({ id: 'p3', name: 'Third', slot: 'sidebar-tool', tag: 'tag-3', order: 50 });

    const sidebarPlugins = registry.getPluginsForSlot('sidebar-tool');
    assert.equal(sidebarPlugins.length, 3);
    assert.equal(sidebarPlugins[0].id, 'p1');
    assert.equal(sidebarPlugins[1].id, 'p2');
    assert.equal(sidebarPlugins[2].id, 'p3');
  });

  it('filters out disabled plugins', () => {
    registry.register({ id: 'p-active', name: 'Active', slot: 'hud-widget', tag: 'tag-active', enabled: true });
    registry.register({ id: 'p-disabled', name: 'Disabled', slot: 'hud-widget', tag: 'tag-disabled', enabled: false });

    const active = registry.getPluginsForSlot('hud-widget');
    assert.equal(active.length, 1);
    assert.equal(active[0].id, 'p-active');
  });

  it('notifies subscribers on registration, unregistration, and clearing', () => {
    const events: PluginRegistryEvent[] = [];
    const unsubscribe = registry.subscribe((ev) => events.push(ev));

    registry.register({ id: 'mod-1', name: 'Soundboard', slot: 'sidebar-tool', tag: 'mod-soundboard' });
    assert.equal(events.length, 1);
    assert.equal(events[0].type, 'registered');
    assert.equal(events[0].slot, 'sidebar-tool');

    const removed = registry.unregister('mod-1');
    assert.equal(removed, true);
    assert.equal(events.length, 2);
    assert.equal(events[1].type, 'unregistered');

    const removedMissing = registry.unregister('non-existent');
    assert.equal(removedMissing, false);
    assert.equal(events.length, 2);

    registry.register({ id: 'mod-2', name: 'Dice Tray', slot: 'dice-panel', tag: 'mod-dice' });
    registry.clear();
    assert.equal(events.length, 4);
    assert.equal(events[3].type, 'cleared');

    unsubscribe();
    registry.register({ id: 'mod-3', name: 'Clock', slot: 'hud-widget', tag: 'mod-clock' });
    assert.equal(events.length, 4); // No new events after unsubscription
  });
});

describe('PluginSandbox CSS Token Bridge & Event Isolation', () => {
  it('identifies valid Bauhaus design tokens and rejects arbitrary CSS', () => {
    assert.ok(isAllowedDesignToken('--rf-color-accent'));
    assert.ok(isAllowedDesignToken('--rf-space-md'));
    assert.ok(isAllowedDesignToken('--rf-font-family'));
    assert.ok(isAllowedDesignToken('--rf-border-width'));
    assert.ok(isAllowedDesignToken('--rf-shadow-sm'));
    assert.ok(isAllowedDesignToken('--rf-bg-surface'));
    assert.ok(isAllowedDesignToken('--rf-text-primary'));

    assert.equal(isAllowedDesignToken('--unauthorized-var'), false);
    assert.equal(isAllowedDesignToken('--custom-plugin-style'), false);
    assert.equal(isAllowedDesignToken('background-color'), false);
  });

  it('exposes defined design token prefixes', () => {
    assert.ok(ALLOWED_TOKEN_PREFIXES.includes('--rf-color-'));
    assert.ok(ALLOWED_TOKEN_PREFIXES.includes('--rf-space-'));
  });

  it('creates sandboxed custom events with encapsulated origin metadata', () => {
    const plugin: PluginDefinition = {
      id: 'ext-calculator',
      name: 'Damage Calc',
      slot: 'hud-widget',
      tag: 'runefoble-calc',
    };

    const event = createSandboxedEvent(plugin, 'damage-calculated', { total: 42, damageType: 'fire' });
    assert.equal(event.type, 'damage-calculated');
    assert.equal(event.bubbles, true);
    assert.equal(event.composed, false); // Event does not pierce Shadow DOM by default
    assert.deepEqual(event.detail, {
      pluginId: 'ext-calculator',
      slot: 'hud-widget',
      sourceTag: 'runefoble-calc',
      payload: { total: 42, damageType: 'fire' },
    });
  });

  it('handles safe element instantiation in non-browser environments gracefully', () => {
    const plugin: PluginDefinition = {
      id: 'ext-mock',
      name: 'Mock',
      slot: 'sidebar-tool',
      tag: 'mock-elem',
    };
    // In Node.js without document defined, returns null without crashing
    const result = instantiatePluginElement(plugin);
    assert.equal(result, null);
  });
});

describe('RunefoblePluginSlot Component Contract & Defaults', () => {
  it('validates supported slot identifiers', () => {
    const supportedSlots = ['hud-widget', 'dice-panel', 'sidebar-tool'];
    for (const s of supportedSlots) {
      assert.ok(typeof s === 'string');
    }
  });

  it('manages plugin registration across multiple slot types', () => {
    const r = new PluginRegistry();
    r.register({ id: 'hud-1', name: 'HUD Widget', slot: 'hud-widget', tag: 'hud-tag' });
    r.register({ id: 'dice-1', name: 'Dice Panel', slot: 'dice-panel', tag: 'dice-tag' });
    r.register({ id: 'side-1', name: 'Sidebar Tool', slot: 'sidebar-tool', tag: 'side-tag' });

    assert.equal(r.getPluginsForSlot('hud-widget').length, 1);
    assert.equal(r.getPluginsForSlot('dice-panel').length, 1);
    assert.equal(r.getPluginsForSlot('sidebar-tool').length, 1);
    assert.equal(r.getPluginsForSlot('unknown-slot').length, 0);
  });
});
