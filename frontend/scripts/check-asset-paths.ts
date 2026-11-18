/**
 * Lint gate for `/assets/` references (TASK-0788).
 *
 * Source files may name an `/assets/...` path. The path must resolve to a file in the
 * `public/` directory of a package that the App Shell or a microfrontend serves. A reference
 * to a file that no package serves fails the gate.
 *
 * Usage (from frontend/, through `pnpm run lint`):
 *   node --experimental-strip-types scripts/check-asset-paths.ts [repoRoot]
 */

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export interface MissingAssetPath {
  file: string;
  line: number;
  assetPath: string;
}

/** A `/assets/` path that starts a token. `/api/v1/assets/x` and prose such as `/assets/...` do not match. */
const ASSET_REFERENCE = /(?<![\w./-])\/assets\/[A-Za-z0-9_][\w./-]*/g;

const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.mjs', '.py']);
const SKIPPED_DIRECTORIES = new Set([
  'node_modules',
  'dist',
  'storybook-static',
  '.venv',
  '__pycache__',
  '.git',
  'public',
  'coverage',
]);
const SCANNED_TREES = ['frontend', 'services', 'libs', 'gateway'];

function childDirectories(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !SKIPPED_DIRECTORIES.has(entry.name))
    .map((entry) => path.join(dir, entry.name));
}

/** Every package directory whose `public/` folder the dev server or a build serves. */
function servedRoots(repoRoot: string): string[] {
  const packages = [
    path.join(repoRoot, 'frontend'),
    ...childDirectories(path.join(repoRoot, 'libs')),
    ...childDirectories(path.join(repoRoot, 'gateway')),
    ...childDirectories(path.join(repoRoot, 'services')).flatMap((service) => [
      service,
      path.join(service, 'ui'),
    ]),
  ];
  return packages
    .map((pkg) => path.join(pkg, 'public'))
    .filter((dir) => existsSync(dir) && statSync(dir).isDirectory());
}

function sourceFiles(dir: string): string[] {
  if (!existsSync(dir)) return [];
  const files: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIPPED_DIRECTORIES.has(entry.name)) files.push(...sourceFiles(full));
    } else if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(full);
    }
  }
  return files;
}

function isServed(assetPath: string, roots: string[]): boolean {
  const relative = assetPath.replace(/^\/+/, '');
  return roots.some((root) => {
    const candidate = path.join(root, relative);
    return existsSync(candidate) && statSync(candidate).isFile();
  });
}

/** Find every `/assets/` reference under the repository that no served package file satisfies. */
export function findMissingAssetPaths(repoRoot: string): MissingAssetPath[] {
  const roots = servedRoots(repoRoot);
  const missing: MissingAssetPath[] = [];
  for (const tree of SCANNED_TREES) {
    for (const file of sourceFiles(path.join(repoRoot, tree))) {
      const lines = readFileSync(file, 'utf8').split('\n');
      lines.forEach((text, index) => {
        for (const match of text.matchAll(ASSET_REFERENCE)) {
          const assetPath = match[0].replace(/\.+$/, '');
          if (!isServed(assetPath, roots)) {
            missing.push({ file, line: index + 1, assetPath });
          }
        }
      });
    }
  }
  return missing;
}

function main(): void {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(scriptDir, '../..');
  const missing = findMissingAssetPaths(repoRoot);
  for (const hit of missing) {
    console.error(
      `${path.relative(repoRoot, hit.file)}:${hit.line}: ${hit.assetPath} is not served by any package public/ directory`,
    );
  }
  if (missing.length > 0) {
    console.error(`check-asset-paths: ${missing.length} missing /assets/ path(s)`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
