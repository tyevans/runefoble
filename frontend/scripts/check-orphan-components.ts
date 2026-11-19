/**
 * Lint gate for orphan components (TASK-0648).
 *
 * A component file under `src/components/` must have an importer in the App Shell source. An
 * importer is any `.ts` file under `src/` that is not a story, not a barrel (`index.ts`), and not
 * the file itself. Relative `import`, `export ... from`, and dynamic `import()` count.
 *
 * Files in OWNER_DECISION_PENDING are reported to the owner and do not fail the gate. Remove an
 * entry when its owner decides to keep the file (with a mounted route) or delete it.
 *
 * Usage (from frontend/, through `pnpm run lint`):
 *   node --experimental-strip-types scripts/check-orphan-components.ts
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export interface OrphanCheckInput {
  /** Component files to check, relative to `frontend/`, for example `src/components/a.ts`. */
  components: string[];
  /** Source text of every module that may import a component, keyed by path relative to `frontend/`. */
  sources: Record<string, string>;
  /** Component files that are exempt from the check. */
  allowlist: Set<string>;
}

/** Owner decision pending (TASK-0648, TASK-0824 F-04). Each file has an open proposed backlog item. */
export const OWNER_DECISION_PENDING: ReadonlySet<string> = new Set([
  'src/components/runefoble-bulletin-board.ts',
  'src/components/minigames/runefoble-merchant-haggler.ts',
  'src/components/minigames/runefoble-minigame-darts.ts',
  'src/components/minigames/runefoble-minigame-liars-dice.ts',
  'src/components/minigames/runefoble-minigame-roulette.ts',
  'src/components/dm-controls/runefoble-dm-negotiation-drawer.ts',
]);

const IMPORT_SPECIFIER = /(?:\bimport\s*(?:[\w*{}\s,]*\sfrom\s*)?|\bexport\s[^;]*?\sfrom\s*|\bimport\s*\()\s*['"]([^'"]+)['"]/g;

/** Returns the component files that no application module imports. Sorted. */
export function findOrphanComponents(input: OrphanCheckInput): string[] {
  const imported = new Set<string>();
  for (const [file, text] of Object.entries(input.sources)) {
    if (!isImporter(file)) continue;
    for (const match of text.matchAll(IMPORT_SPECIFIER)) {
      const specifier = match[1];
      if (!specifier.startsWith('.')) continue;
      imported.add(path.posix.normalize(path.posix.join(path.posix.dirname(file), specifier)));
    }
  }
  return input.components
    .filter((file) => !isBarrelOrStory(file) && !input.allowlist.has(file) && !imported.has(file))
    .sort();
}

function isBarrelOrStory(file: string): boolean {
  return path.posix.basename(file) === 'index.ts' || file.endsWith('.stories.ts');
}

function isImporter(file: string): boolean {
  return file.startsWith('src/') && file.endsWith('.ts') && !isBarrelOrStory(file);
}

function listFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? listFiles(full) : [full];
  });
}

function main(): void {
  const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const toRelative = (full: string) => path.relative(frontendRoot, full).split(path.sep).join('/');
  const all = listFiles(path.join(frontendRoot, 'src')).filter((f) => f.endsWith('.ts')).map(toRelative);
  const components = all.filter((f) => f.startsWith('src/components/'));
  const sources: Record<string, string> = {};
  for (const file of all) sources[file] = readFileSync(path.join(frontendRoot, file), 'utf8');
  const orphans = findOrphanComponents({ components, sources, allowlist: OWNER_DECISION_PENDING });
  for (const file of orphans) {
    console.error(`${file}: no application module imports this component`);
  }
  if (orphans.length > 0) {
    console.error(`check-orphan-components: ${orphans.length} orphan component(s)`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
