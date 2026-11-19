/**
 * OBS party vitals route (TASK-0823 review).
 *
 * The App Shell route `#/overlay/party-vitals/:sessionId` must mount the vendored
 * `<runefoble-spectator-overlay>` with the session id and the query values. The owner read
 * is replaced by a stub, so the test checks what the page passes on, not the gateway.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { Router } from '../src/router/router.ts';
import { resolveActiveView } from '../src/router/view-resolver.ts';
import {
  DEFAULT_OVERLAY_EASING,
  parsePartyVitalsOverlayQuery,
  toOverlayCamera,
  toOverlayParty,
  type PartyVitalsReply,
} from '../src/app/party-vitals-overlay.ts';
import '../src/components/runefoble-party-vitals-page.ts';

const EASING = 'cubic-bezier(0.42, 0.0, 0.58, 1.0)';
const REPLY: PartyVitalsReply = {
  session_id: 'sess-obs-1',
  party: [{ id: 't1', name: 'Valeros', hp: 45, max_hp: 45 }],
  camera: {
    target_x: 2,
    target_y: 3,
    zoom: 1.5,
    duration_ms: 300,
    easing: DEFAULT_OVERLAY_EASING,
    active_token_id: 't1',
    reason: 'turn_started',
  },
  round: 1,
  position: 'sidebar',
  transparent: true,
};

type Page = HTMLElement & {
  sessionId: string;
  position: string;
  easing: string;
  duration: number;
  fetcher: (sessionId: string, position: string) => Promise<unknown>;
};

async function waitFor<T>(read: () => T | null | undefined): Promise<T> {
  for (let i = 0; i < 100; i += 1) {
    const value = read();
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error('The condition did not hold in time.');
}

afterEach(() => {
  document.querySelectorAll('runefoble-party-vitals-page').forEach((el) => el.remove());
  document.documentElement.classList.remove('obs-transparent');
});

describe('OBS party vitals route', () => {
  it('resolves the overlay route to its own view and matches the session id', () => {
    const router = new Router();
    router.reset();
    const matched = router.match('#/overlay/party-vitals/sess-obs-1?position=sidebar&duration=400');
    expect(matched?.pattern).toBe('#/overlay/party-vitals/:sessionId');
    expect(matched?.params.sessionId).toBe('sess-obs-1');
    expect(matched?.query).toEqual({ position: 'sidebar', duration: '400' });
    expect(resolveActiveView(matched)).toBe('party-vitals-overlay');
  });

  it('reads the position, easing and duration query values', () => {
    expect(parsePartyVitalsOverlayQuery({ position: 'top', easing: EASING, duration: '400' })).toEqual({
      position: 'top',
      easing: EASING,
      durationMs: 400,
    });
  });

  it('falls back to the defaults for missing or malformed query values', () => {
    expect(parsePartyVitalsOverlayQuery({})).toEqual({
      position: 'bottom',
      easing: DEFAULT_OVERLAY_EASING,
      durationMs: 300,
    });
    expect(
      parsePartyVitalsOverlayQuery({ position: 'left', easing: 'url(evil)', duration: '99999' }),
    ).toEqual({ position: 'bottom', easing: DEFAULT_OVERLAY_EASING, durationMs: 300 });
  });

  it('maps the owner party and camera to the overlay component shape', () => {
    expect(toOverlayParty(REPLY.party)).toEqual([{ id: 't1', name: 'Valeros', hp: 45, maxHp: 45 }]);
    expect(toOverlayCamera(REPLY.camera)).toMatchObject({ targetX: 2, targetY: 3, durationMs: 300, activeTokenId: 't1' });
  });

  it('mounts the overlay with the session id and the query values', async () => {
    const calls: unknown[][] = [];
    const page = document.createElement('runefoble-party-vitals-page') as Page;
    page.sessionId = 'sess-obs-1';
    page.position = 'sidebar';
    page.easing = EASING;
    page.duration = 400;
    page.fetcher = async (sessionId, position) => {
      calls.push([sessionId, position]);
      return { ok: true, data: REPLY };
    };
    document.body.append(page);

    const overlay = await waitFor(() => page.shadowRoot?.querySelector('runefoble-spectator-overlay'));
    expect(calls).toEqual([['sess-obs-1', 'sidebar']]);
    expect(overlay.getAttribute('session-id')).toBe('sess-obs-1');
    expect(overlay.getAttribute('position')).toBe('sidebar');
    expect(overlay.hasAttribute('transparent-mode')).toBe(true);
    expect(overlay.getAttribute('style')).toContain('--overlay-duration: 400ms');
    expect(overlay.getAttribute('style')).toContain(EASING);
    expect(document.documentElement.classList.contains('obs-transparent')).toBe(true);
  });

  it('shows the owner refusal and mounts no overlay when the read fails', async () => {
    const page = document.createElement('runefoble-party-vitals-page') as Page;
    page.sessionId = 'sess-obs-2';
    page.position = 'bottom';
    page.fetcher = async () => ({ ok: false, status: 403, message: 'Forbidden' });
    document.body.append(page);

    const alert = await waitFor(() => page.shadowRoot?.querySelector('[role="alert"]'));
    expect(alert.textContent).toContain('Forbidden');
    expect(page.shadowRoot?.querySelector('runefoble-spectator-overlay')).toBeNull();
  });

  it('removes the transparent document class when the page leaves the document', async () => {
    const page = document.createElement('runefoble-party-vitals-page') as Page;
    page.sessionId = 'sess-obs-3';
    page.fetcher = async () => ({ ok: true, data: REPLY });
    document.body.append(page);
    await waitFor(() => page.shadowRoot?.querySelector('runefoble-spectator-overlay'));
    page.remove();
    expect(document.documentElement.classList.contains('obs-transparent')).toBe(false);
  });
});
