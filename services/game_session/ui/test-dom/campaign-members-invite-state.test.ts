/**
 * Invite link field state (TASK-0973, ADR-0015). While the App Shell waits for a Generate reply,
 * the field and Copy Link are empty and disabled. Copy writes only the link the field shows now.
 * The test reads the rendered DOM, as a DM would.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/campaigns/runefoble-campaign-members.ts';

type Members = HTMLElement & { updateComplete: Promise<boolean>; openInviteModal(): void; inviteUrl: string };

const original = Object.getOwnPropertyDescriptor(navigator, 'clipboard');

function useClipboard(writeText: (text: string) => Promise<void>): void {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
}

async function mount(attrs: { inviteUrl?: string; pending?: boolean }): Promise<Members> {
  const el = document.createElement('runefoble-campaign-members') as Members;
  el.setAttribute('campaign-id', 'camp-1');
  el.toggleAttribute('can-manage', true);
  if (attrs.inviteUrl) el.setAttribute('invite-url', attrs.inviteUrl);
  el.toggleAttribute('invite-pending', attrs.pending ?? false);
  document.body.append(el);
  await el.updateComplete;
  el.openInviteModal();
  await el.updateComplete;
  return el;
}

function query<T extends Element>(el: Members, selector: string): T | null {
  return el.shadowRoot?.querySelector<T>(selector) ?? null;
}

afterEach(() => {
  document.querySelectorAll('runefoble-campaign-members').forEach((el) => el.remove());
  if (original) Object.defineProperty(navigator, 'clipboard', original);
  else delete (navigator as unknown as Record<string, unknown>).clipboard;
});

describe('runefoble-campaign-members invite link field state', () => {
  it('shows an empty, disabled link field and Copy Link while a request is out', async () => {
    const el = await mount({ pending: true });

    const input = query<HTMLInputElement>(el, '.invite-link-input');
    expect(input).not.toBeNull();
    expect(input?.value).toBe('');
    expect(input?.disabled).toBe(true);
    expect(query<HTMLButtonElement>(el, '.btn-copy')?.disabled).toBe(true);
  });

  it('disables Generate Link while a request is out', async () => {
    const el = await mount({ pending: true });

    expect(query<HTMLButtonElement>(el, '.btn-generate-link')?.disabled).toBe(true);
  });

  it('shows no link field after a refused request (no link, no request pending)', async () => {
    const el = await mount({});

    expect(query(el, '.invite-link-input')).toBeNull();
    expect(query(el, '.btn-copy')).toBeNull();
  });

  it('copies the newest link only, never the link it showed before', async () => {
    const written: string[] = [];
    useClipboard(async (t) => { written.push(t); });
    const el = await mount({ inviteUrl: 'https://runefoble.test/#/join/tok-old' });
    el.inviteUrl = 'https://runefoble.test/#/join/tok-new';
    await el.updateComplete;

    expect(query<HTMLInputElement>(el, '.invite-link-input')?.value).toBe('https://runefoble.test/#/join/tok-new');
    (query<HTMLButtonElement>(el, '.btn-copy') as HTMLButtonElement).click();

    await expect.poll(() => written.length).toBe(1);
    expect(written).toEqual(['https://runefoble.test/#/join/tok-new']);
  });
});
