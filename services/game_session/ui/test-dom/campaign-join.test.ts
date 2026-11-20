/**
 * The join view of an invite link (ADR-0023, TASK-0950). `<runefoble-campaign-join>` runs in
 * headless Chromium. Each test reads the rendered text and the events, as the App Shell does.
 * The token is an input of the element. The tests check that it is never rendered.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/campaigns/runefoble-campaign-join.ts';

type JoinEl = HTMLElement & {
  updateComplete: Promise<boolean>;
  phase: string;
  message: string;
};

const TOKEN = 'tok-join-secret-42';

async function mount(attrs: Record<string, string>): Promise<JoinEl> {
  const el = document.createElement('runefoble-campaign-join') as JoinEl;
  for (const [name, value] of Object.entries(attrs)) el.setAttribute(name, value);
  document.body.append(el);
  await el.updateComplete;
  return el;
}

function text(el: JoinEl): string {
  return el.shadowRoot?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

function button(el: JoinEl, label: string): HTMLButtonElement {
  const found = Array.from(el.shadowRoot?.querySelectorAll('button') ?? []).find((b) => b.textContent?.trim() === label);
  if (!found) throw new Error(`No button "${label}"`);
  return found;
}

function type(el: JoinEl, selector: string, value: string): void {
  const input = el.shadowRoot?.querySelector(selector) as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

afterEach(() => {
  document.querySelectorAll('runefoble-campaign-join').forEach((el) => el.remove());
});

describe('runefoble-campaign-join', () => {
  it('shows nothing when the token is missing', async () => {
    const el = await mount({ phase: 'account-form' });
    expect(el.shadowRoot?.querySelector('.join-card')).toBeNull();
    expect(text(el)).toBe('');
  });

  it('sends the trimmed form values and the token when a signed-out person creates an account', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'account-form' });
    const details: unknown[] = [];
    el.addEventListener('account-requested', (e) => details.push((e as CustomEvent).detail));

    type(el, 'input[name="displayName"]', '  Sarah  ');
    type(el, 'input[name="email"]', ' sarah@example.test ');
    el.shadowRoot?.querySelector('form')?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));

    expect(details).toEqual([{ inviteToken: TOKEN, email: 'sarah@example.test', displayName: 'Sarah' }]);
  });

  it('tells the person to read the e-mail and sign in after the account is accepted', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'account-accepted' });
    expect(text(el)).toContain('Zitadel sent a message to your e-mail address');
    expect(text(el)).not.toContain(TOKEN);

    let signIn = 0;
    el.addEventListener('sign-in-requested', () => { signIn += 1; });
    button(el, 'Sign in').click();
    expect(signIn).toBe(1);
  });

  it('shows the join button only to a signed-in person and sends the join request', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'join-ready' });
    expect(el.shadowRoot?.querySelector('input[name="email"]')).toBeNull();

    const requests: unknown[] = [];
    el.addEventListener('join-requested', (e) => requests.push((e as CustomEvent).detail));
    button(el, 'Join campaign').click();

    expect(requests).toEqual([{ inviteToken: TOKEN }]);
  });

  it('shows the server refusal text and never the token', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'join-refused', message: 'This invite link is not valid.' });
    expect(el.shadowRoot?.querySelector('[role="alert"]')?.textContent).toContain('This invite link is not valid.');
    expect(text(el)).not.toContain(TOKEN);
  });

  it('links to the campaign after a join', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'joined', 'campaign-id': 'camp-9', 'member-role': 'player' });
    expect(text(el)).toContain('You joined this campaign as player');
    const link = el.shadowRoot?.querySelector('a.join-link') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('#/campaigns/camp-9');
  });

  it('disables the account form while the request runs', async () => {
    const el = await mount({ 'invite-token': TOKEN, phase: 'account-sending' });
    expect((button(el, 'Creating account...') as HTMLButtonElement).disabled).toBe(true);
    expect((el.shadowRoot?.querySelector('input[name="email"]') as HTMLInputElement).disabled).toBe(true);
  });
});
