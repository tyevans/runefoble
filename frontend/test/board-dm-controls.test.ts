/**
 * Board DM Controls in the App Shell (TASK-0685).
 *
 * The DM trap controls take their target cell from the board move dispatch. The DM trap
 * controls are not a sidebar plugin. The App Shell mounts them with the board id.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveBoardDmAccess, targetFromMoveDispatch } from '../src/app/board-dm-controls.ts';
import { registerDefaultPlugins, pluginRegistry } from '../src/components/plugins/plugin_registry.ts';

describe('targetFromMoveDispatch', () => {
  it('returns the destination cell of a move dispatch as targetX and targetY', () => {
    assert.deepEqual(targetFromMoveDispatch({ tokenId: 'valeros', toX: 4, toY: 7 }), { targetX: 4, targetY: 7 });
  });

  it('returns the origin cell (zero) as a valid target', () => {
    assert.deepEqual(targetFromMoveDispatch({ tokenId: 'valeros', toX: 0, toY: 0 }), { targetX: 0, targetY: 0 });
  });

  it('returns null for a missing coordinate instead of a guessed cell', () => {
    assert.equal(targetFromMoveDispatch({ tokenId: 'valeros', toX: 4 }), null);
    assert.equal(targetFromMoveDispatch(null), null);
  });

  it('returns null for a fractional or negative coordinate', () => {
    assert.equal(targetFromMoveDispatch({ tokenId: 'valeros', toX: 2.5, toY: 1 }), null);
    assert.equal(targetFromMoveDispatch({ tokenId: 'valeros', toX: -1, toY: 1 }), null);
  });
});

describe('resolveBoardDmAccess', () => {
  it('allows the board DM controls only when the caller holds run_session', () => {
    assert.equal(resolveBoardDmAccess({ run_session: true }), 'allowed');
    assert.equal(resolveBoardDmAccess({ run_session: false }), 'denied');
    assert.equal(resolveBoardDmAccess(undefined), 'denied');
  });
});

describe('DM trap controls mount', () => {
  it('is not a sidebar plugin, because the App Shell mounts it with the board id', () => {
    registerDefaultPlugins(pluginRegistry, true);
    const tags = pluginRegistry.getPluginsForSlot('sidebar-tool').map((p) => p.tag);
    assert.equal(tags.includes('runefoble-dm-trap-controls'), false);
    assert.equal(tags.includes('runefoble-dm-whisper-bar'), true);
    registerDefaultPlugins(pluginRegistry, false);
  });
});
