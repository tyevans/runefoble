/**
 * Invite link copy never shows success after a clipboard error (TASK-0908, ADR-0015).
 * `<runefoble-campaign-members>` runs in headless Chromium. The system clipboard is the
 * process boundary, so each test sets `navigator.clipboard` to accept or refuse the write.
 * The test reads the rendered text, as a player would.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/campaigns/runefoble-campaign-members.ts';

type Members = HTMLElement & { updateComplete: Promise<boolean>; openInviteModal(): void };

const original = Object.getOwnPropertyDescriptor(navigator, 'clipboard');

function useClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
}

async function mountOpen(): Promise<Members> {
  const el = document.createElement('runefoble-campaign-members') as Members;
  el.setAttribute('campaign-id', 'camp-1');
  el.setAttribute('invite-url', 'https://runefoble.test/#/join/tok-1');
  el.toggleAttribute('can-manage', true);
  document.body.append(el);
  await el.updateComplete;
  el.openInviteModal();
  await el.updateComplete;
  return el;
}

function text(el: Members): string {
  return el.shadowRoot?.textContent?.replace(/\s+/g, ' ') ?? '';
}

async function clickCopy(el: Members): Promise<void> {
  (el.shadowRoot?.querySelector('.btn-copy') as HTMLButtonElement).click();
}

afterEach(() => {
  document.querySelectorAll('runefoble-campaign-members').forEach((el) => el.remove());
  if (original) Object.defineProperty(navigator, 'clipboard', original);
  else delete (navigator as unknown as Record<string, unknown>).clipboard;
});

describe('runefoble-campaign-members invite copy', () => {
  it('shows "Copied" only after the clipboard accepts the link', async () => {
    const written: string[] = [];
    useClipboard(async (t) => { written.push(t); });
    const el = await mountOpen();
    let events = 0;
    el.addEventListener('copy-invite-link', () => { events += 1; });

    await clickCopy(el);

    await expect.poll(() => text(el)).toContain('Copied to clipboard!');
    expect(written).toEqual(['https://runefoble.test/#/join/tok-1']);
    expect(events).toBe(1);
  });

  it('shows the copy error and no success text when the clipboard refuses', async () => {
    useClipboard(async () => { throw new DOMException('Write permission denied.', 'NotAllowedError'); });
    const el = await mountOpen();
    let events = 0;
    el.addEventListener('copy-invite-link', () => { events += 1; });

    await clickCopy(el);

    await expect.poll(() => text(el)).toContain('Copy failed. Select the link and copy it.');
    expect(text(el)).not.toContain('Copied');
    expect(events).toBe(0);
  });

  it('shows the copy error when the browser has no clipboard', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
    const el = await mountOpen();

    await clickCopy(el);

    await expect.poll(() => text(el)).toContain('Copy failed. Select the link and copy it.');
    expect(text(el)).not.toContain('Copied');
  });
});
