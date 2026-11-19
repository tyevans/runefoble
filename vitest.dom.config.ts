/**
 * Shared browser harness for Lit element tests (TASK-0797).
 *
 * Each UI package keeps a small `vitest.config.ts` that calls `domTestConfig` with its own
 * directory. Tests live in `test-dom/` and run in headless Chromium through Playwright.
 * Node-only unit tests stay in `test/` and run with `node --test`.
 * A package that needs a live loopback upstream passes `loopbackUpstreamCommands` (TASK-0758).
 *
 * The browser API server listens on 127.0.0.1 at a port that the operating system picks
 * (TASK-0909). The fixed default port 63315 let parallel runs in other worktrees block each
 * other. `strictPort: false` lets Vite move on if another process takes the port first.
 */

import { createServer } from 'node:net';
import { playwright } from '@vitest/browser-playwright';
import { defineConfig } from 'vitest/config';
import type { BrowserCommand } from 'vitest/node';

export interface DomTestOptions {
  /** Node-side commands that tests call through `commands` from `vitest/browser`. */
  commands?: Record<string, BrowserCommand<any>>;
}

const BROWSER_API_HOST = '127.0.0.1';

/** Asks the operating system for a free TCP port on the browser API host. */
function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', reject);
    probe.listen(0, BROWSER_API_HOST, () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('The port probe did not return a TCP address.'));
        return;
      }
      probe.close(() => resolve(address.port));
    });
  });
}

export async function domTestConfig(packageDir: string, options: DomTestOptions = {}) {
  const port = await freePort();
  return defineConfig({
    root: packageDir,
    test: {
      include: ['test-dom/**/*.test.ts'],
      // The loopback upstream is one server for the whole run. Its reply and request log are
      // shared, so test files that use it must run one after another (TASK-0922).
      fileParallelism: options.commands === undefined,
      browser: {
        enabled: true,
        headless: true,
        provider: playwright(),
        instances: [{ browser: 'chromium' }],
        // Failure screenshots would land in the source tree.
        screenshotFailures: false,
        api: { host: BROWSER_API_HOST, port, strictPort: false },
        commands: options.commands,
      },
    },
  });
}
