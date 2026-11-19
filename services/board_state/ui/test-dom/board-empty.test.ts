/**
 * No-battlemap-yet empty state (TASK-0906).
 * `<runefoble-board-empty>` runs in headless Chromium. The test reads the rendered text,
 * as a user would.
 * Governing ADRs: ADR-0013, ADR-0015.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/runefoble-board-empty.ts';
import type { RunefobleBoardEmpty } from '../src/runefoble-board-empty.ts';

async function mount(canSetUpMap: boolean): Promise<RunefobleBoardEmpty> {
  const el = document.createElement('runefoble-board-empty');
  el.canSetUpMap = canSetUpMap;
  document.body.append(el);
  await el.updateComplete;
  return el;
}

afterEach(() => document.querySelectorAll('runefoble-board-empty').forEach((el) => el.remove()));

describe('runefoble-board-empty', () => {
  it('tells a player that the session has no battlemap yet, without a DM hint', async () => {
    const el = await mount(false);
    const status = el.shadowRoot?.querySelector('[role="status"]');
    expect(status?.textContent).toContain('No battlemap yet');
    expect(el.shadowRoot?.querySelector('[data-testid="board-empty-dm-hint"]')).toBeNull();
  });

  it('shows the DM a hint to set up a map', async () => {
    const el = await mount(true);
    const hint = el.shadowRoot?.querySelector('[data-testid="board-empty-dm-hint"]');
    expect(hint?.textContent).toContain('Set up a battlemap');
  });
});
