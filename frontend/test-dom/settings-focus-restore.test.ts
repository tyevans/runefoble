/**
 * Settings focus restore (TASK-0761). The shell renders in a real Chromium DOM.
 *
 * When the settings modal closes, focus goes back to the control that opened it. The shell
 * asks the header to restore focus through the public `restoreFocus` method. The shell does
 * not read the header shadow root. The tests close the modal through its public event and
 * check where focus goes.
 * Governing ADRs: ADR-0004, ADR-0013.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/components/runefoble-header.ts';
import type { RunefobleHeader } from '../src/components/runefoble-header.ts';

afterEach(() => {
  document.body.replaceChildren();
});

async function mountHeader(): Promise<RunefobleHeader> {
  const header = document.createElement('runefoble-header');
  document.body.append(header);
  await header.updateComplete;
  return header;
}

describe('runefoble-header restoreFocus', () => {
  it('moves focus to the settings control', async () => {
    const other = document.createElement('button');
    document.body.append(other);
    const header = await mountHeader();
    other.focus();

    header.restoreFocus();

    expect(document.activeElement).toBe(header);
    expect(header.shadowRoot?.activeElement?.getAttribute('aria-label')).toBe('Open settings');
  });
});

describe('runefoble-app settings modal close', () => {
  it('returns focus to the header settings control', async () => {
    await import('../src/runefoble-app.ts');
    const app = document.createElement('runefoble-app');
    document.body.append(app);
    await app.updateComplete;
    app.isSettingsOpen = true;
    await app.updateComplete;
    const modal = app.shadowRoot?.querySelector('runefoble-settings-modal');
    const header = app.shadowRoot?.querySelector('runefoble-header');
    expect(modal).toBeTruthy();
    await modal?.updateComplete;
    await new Promise((resolve) => requestAnimationFrame(resolve));

    modal?.closeModal();
    await app.updateComplete;
    await modal?.updateComplete;

    expect(app.isSettingsOpen).toBe(false);
    expect(app.shadowRoot?.activeElement).toBe(header);
    expect(header?.shadowRoot?.activeElement?.getAttribute('aria-label')).toBe('Open settings');
  });
});
