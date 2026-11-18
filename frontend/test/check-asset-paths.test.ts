/**
 * Unit tests for the `/assets/` lint gate (TASK-0788).
 * The gate fails when source names an `/assets/` path that no package serves.
 * Each test builds a small repository tree in a temporary directory.
 */

import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findMissingAssetPaths } from '../scripts/check-asset-paths.ts';

/** Built from a prefix so this file does not name a missing path for the gate that it tests. */
const ASSET = '/assets/';

const SCRIPT = fileURLToPath(new URL('../scripts/check-asset-paths.ts', import.meta.url));

const roots: string[] = [];

function makeRepo(files: Record<string, string>): string {
  const root = mkdtempSync(path.join(os.tmpdir(), 'asset-gate-'));
  roots.push(root);
  for (const [relative, content] of Object.entries(files)) {
    const target = path.join(root, relative);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, content);
  }
  return root;
}

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

describe('check-asset-paths lint gate', () => {
  it('passes when every referenced /assets/ path is served by a package', () => {
    const root = makeRepo({
      [`frontend/public${ASSET}portraits/fighter.svg`]: '<svg/>',
      'frontend/src/app.ts': `const img = '${ASSET}portraits/fighter.svg';\n`,
    });

    assert.deepEqual(findMissingAssetPaths(root), []);
  });

  it('reports a planted missing /assets/ path with its file and line', () => {
    const root = makeRepo({
      [`frontend/public${ASSET}portraits/fighter.svg`]: '<svg/>',
      'services/character_sheet/ui/src/card.ts': `const ok = 1;\nconst src = "${ASSET}portraits/ghost.svg";\n`,
    });

    const missing = findMissingAssetPaths(root);

    assert.equal(missing.length, 1);
    assert.equal(missing[0].assetPath, `${ASSET}portraits/ghost.svg`);
    assert.equal(missing[0].line, 2);
    assert.match(missing[0].file, /services[/\\]character_sheet[/\\]ui[/\\]src[/\\]card\.ts$/);
  });

  it('ignores API routes that merely contain the word assets and prose placeholders', () => {
    const root = makeRepo({
      'frontend/src/client.ts': "const url = '/api/v1/assets/upload';\n",
      'frontend/src/profile.ts': `placeholder="https://... or ${ASSET}..."\n`,
    });

    assert.deepEqual(findMissingAssetPaths(root), []);
  });

  it('exits non-zero for a planted missing path and zero for a clean tree', () => {
    const dirty = makeRepo({
      'frontend/src/app.ts': `const img = '${ASSET}nowhere.svg';\n`,
    });
    const clean = makeRepo({
      [`frontend/public${ASSET}ok.svg`]: '<svg/>',
      'frontend/src/app.ts': `const img = '${ASSET}ok.svg';\n`,
    });

    const run = (root: string) =>
      spawnSync(process.execPath, ['--experimental-strip-types', SCRIPT, root], { encoding: 'utf8' });

    const failed = run(dirty);
    assert.equal(failed.status, 1, failed.stderr);
    assert.match(failed.stderr, /\/assets\/nowhere\.svg/);

    const passed = run(clean);
    assert.equal(passed.status, 0, passed.stderr);
  });
});
