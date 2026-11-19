/**
 * Behaviour of the orphan component check (TASK-0648). The check reads a set of source files and
 * reports each component file that no application module imports. Stories, barrels (index.ts),
 * and allowlisted owner-decision files do not count.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { findOrphanComponents } from '../scripts/check-orphan-components.ts';

const COMPONENTS = [
  'src/components/runefoble-used.ts',
  'src/components/runefoble-only-story.ts',
  'src/components/runefoble-only-barrel.ts',
  'src/components/runefoble-chained.ts',
  'src/components/runefoble-chain-leaf.ts',
  'src/components/runefoble-allowlisted.ts',
  'src/components/index.ts',
];

describe('findOrphanComponents', () => {
  it('reports a component that no application module imports', () => {
    const orphans = findOrphanComponents({
      components: COMPONENTS,
      sources: {
        'src/runefoble-app.ts': "import './components/runefoble-used.ts';",
        'src/components/runefoble-chained.ts': "import './runefoble-chain-leaf.ts';",
        'src/components/runefoble-only-story.ts': '',
        'src/components/runefoble-only-barrel.ts': '',
        'src/components/index.ts': "export * from './runefoble-only-barrel.ts';",
        'src/stories/runefoble-only-story.stories.ts': "import '../components/runefoble-only-story.ts';",
      },
      allowlist: new Set(['src/components/runefoble-allowlisted.ts']),
    });
    assert.deepEqual(orphans, [
      'src/components/runefoble-chained.ts',
      'src/components/runefoble-only-barrel.ts',
      'src/components/runefoble-only-story.ts',
    ]);
  });

  it('counts a dynamic import as an importer', () => {
    const orphans = findOrphanComponents({
      components: ['src/components/runefoble-lazy.ts'],
      sources: { 'src/app/registry.ts': "const load = () => import('../components/runefoble-lazy.ts');" },
      allowlist: new Set(),
    });
    assert.deepEqual(orphans, []);
  });

  it('does not report an allowlisted file even when nothing imports it', () => {
    const orphans = findOrphanComponents({
      components: ['src/components/runefoble-allowlisted.ts'],
      sources: {},
      allowlist: new Set(['src/components/runefoble-allowlisted.ts']),
    });
    assert.deepEqual(orphans, []);
  });
});
