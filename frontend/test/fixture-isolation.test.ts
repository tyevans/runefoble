/**
 * Fixture Isolation Invariant (TASK-0640).
 *
 * Canned fixture data may be imported only by Storybook stories and unit tests.
 * No production module under src/ (outside src/fixtures/ and *.stories.ts) may import
 * fixtures, and no source may reference the retired FALLBACK_* services layer.
 * Governing ADRs: ADR-0004, ADR-0007
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_DIR = resolve(__dirname, '../src');
const FIXTURE_IMPORT = /from\s+['"][^'"]*fixtures\/[^'"]*['"]|from\s+['"][^'"]*fallback-data[^'"]*['"]/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return full.endsWith('.ts') ? [full] : [];
  });
}

describe('TASK-0640: Fixture imports are confined to stories and tests', () => {
  const productionFiles = sourceFiles(SRC_DIR).filter((file) => {
    const rel = relative(SRC_DIR, file);
    return !rel.startsWith('fixtures/') && !rel.endsWith('.stories.ts');
  });

  it('scans a non-trivial set of production sources', () => {
    assert.ok(productionFiles.length > 20, `expected many production sources, found ${productionFiles.length}`);
  });

  it('no production module imports a fixture or fallback-data module', () => {
    const offenders = productionFiles
      .filter((file) => FIXTURE_IMPORT.test(readFileSync(file, 'utf-8')))
      .map((file) => relative(SRC_DIR, file));
    assert.deepEqual(offenders, [], `production modules import fixtures: ${offenders.join(', ')}`);
  });

  it('no production module references the retired FALLBACK_ identifiers', () => {
    const offenders = productionFiles
      .filter((file) => /\bFALLBACK_[A-Z_]+\b/.test(readFileSync(file, 'utf-8')))
      .map((file) => relative(SRC_DIR, file));
    assert.deepEqual(offenders, [], `production modules reference FALLBACK_: ${offenders.join(', ')}`);
  });
});
