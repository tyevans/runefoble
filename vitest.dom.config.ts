/**
 * Shared browser harness for Lit element tests (TASK-0797).
 *
 * Each UI package keeps a small `vitest.config.ts` that calls `domTestConfig` with its own
 * directory. Tests live in `test-dom/` and run in headless Chromium through Playwright.
 * Node-only unit tests stay in `test/` and run with `node --test`.
 * A package that needs a live loopback upstream passes `loopbackUpstreamCommands` (TASK-0758).
 */

import { playwright } from '@vitest/browser-playwright';
import { defineConfig } from 'vitest/config';
import type { BrowserCommand } from 'vitest/node';

export interface DomTestOptions {
  /** Node-side commands that tests call through `commands` from `vitest/browser`. */
  commands?: Record<string, BrowserCommand<any>>;
}

export function domTestConfig(packageDir: string, options: DomTestOptions = {}) {
  return defineConfig({
    root: packageDir,
    test: {
      include: ['test-dom/**/*.test.ts'],
      browser: {
        enabled: true,
        headless: true,
        provider: playwright(),
        instances: [{ browser: 'chromium' }],
        // Failure screenshots would land in the source tree.
        screenshotFailures: false,
        commands: options.commands,
      },
    },
  });
}
