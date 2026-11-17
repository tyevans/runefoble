/**
 * App Shell source reader for source-level wiring checks (TASK-0640b).
 *
 * The App Shell is split between runefoble-app.ts and the modules in src/app/.
 * Wiring checks read both, so they assert on the shell as a whole.
 */

import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const APP_DIR = fileURLToPath(new URL('../../src/app/', import.meta.url));
const APP_FILE = fileURLToPath(new URL('../../src/runefoble-app.ts', import.meta.url));

/** Returns runefoble-app.ts followed by every src/app/ module, joined by newlines. */
export function readAppShellSource(): string {
  const modules = readdirSync(APP_DIR).filter((f) => f.endsWith('.ts')).sort();
  return [APP_FILE, ...modules.map((f) => APP_DIR + f)].map((p) => readFileSync(p, 'utf-8')).join('\n');
}
