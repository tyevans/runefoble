/**
 * Push to Talk on `<runefoble-voice-controls>` (TASK-0946).
 * The element runs in headless Chromium with a fake microphone (a generated tone). Playwright
 * holds the real button and the real Space key. The test reads the emitted `voice-utterance`
 * and the rendered text, as the App Shell and a user would.
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0015.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { userEvent } from 'vitest/browser';
import '../src/runefoble-voice-controls.ts';
import type { RunefobleVoiceControls, VoiceUtteranceDetail } from '../src/runefoble-voice-controls.ts';

const HOLD_MS = 700;

async function mount(): Promise<RunefobleVoiceControls> {
  const el = document.createElement('runefoble-voice-controls');
  document.body.append(el);
  await el.updateComplete;
  return el;
}

function button(el: RunefobleVoiceControls): HTMLButtonElement {
  const found = el.shadowRoot?.querySelector<HTMLButtonElement>('.mic-button');
  if (!found) throw new Error('No Push to Talk button');
  return found;
}

function text(el: RunefobleVoiceControls, selector: string): string {
  return el.shadowRoot?.querySelector(selector)?.textContent?.trim() ?? '';
}

function nextUtterance(el: RunefobleVoiceControls): Promise<VoiceUtteranceDetail> {
  return new Promise((resolve) => {
    el.addEventListener('voice-utterance', (e) => resolve((e as CustomEvent<VoiceUtteranceDetail>).detail), { once: true });
  });
}

function decodeWav(base64: string): DataView {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  return new DataView(bytes.buffer);
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

afterEach(() => {
  document.body.replaceChildren();
});

describe('<runefoble-voice-controls> Push to Talk', () => {
  it('records while the button is held and emits a 16 kHz mono WAV on release', async () => {
    const el = await mount();
    const utterance = nextUtterance(el);

    const target = button(el);
    const box = target.getBoundingClientRect();
    await userEvent.hover(target);
    target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, clientX: box.x + 5, clientY: box.y + 5 }));
    await el.updateComplete;
    expect(el.holding).toBe(true);
    expect(text(el, '.mic-button')).toContain('Release to Send');
    await wait(HOLD_MS);
    target.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, button: 0 }));

    const wav = decodeWav((await utterance).audioBase64);
    expect(wav.getUint32(0, false)).toBe(0x52494646); // "RIFF"
    expect(wav.getUint16(22, true)).toBe(1);
    expect(wav.getUint32(24, true)).toBe(16000);
    expect(wav.getUint16(34, true)).toBe(16);
    const dataBytes = wav.getUint32(40, true);
    expect(dataBytes).toBeGreaterThan(16000 * 2 * 0.3);
    expect(el.holding).toBe(false);
  });

  it('records while the Space key is held on the focused button', async () => {
    const el = await mount();
    const utterance = nextUtterance(el);

    button(el).focus();
    await userEvent.keyboard('{Space>}');
    await wait(HOLD_MS);
    await userEvent.keyboard('{/Space}');

    const wav = decodeWav((await utterance).audioBase64);
    expect(wav.getUint32(24, true)).toBe(16000);
    expect(wav.getUint32(40, true)).toBeGreaterThan(0);
  });

  it('shows the transcript that the App Shell sets', async () => {
    const el = await mount();
    el.transcript = 'move two squares north';
    await el.updateComplete;

    expect(text(el, '.utterance-transcript')).toBe('move two squares north');
    expect(el.shadowRoot?.querySelector('[role="alert"]')).toBeNull();
  });

  it('shows a Watcher error next to the transcript', async () => {
    const el = await mount();
    el.transcript = 'move two squares north';
    el.watcherError = 'The Watcher answered 503';
    await el.updateComplete;

    expect(text(el, '.watcher-error')).toContain('The Watcher answered 503');
  });

  it('shows a failed upload as an alert and no transcript', async () => {
    const el = await mount();
    el.uploadError = 'Push to Talk failed (503): The speech engine is unavailable.';
    el.transcript = '';
    await el.updateComplete;

    expect(text(el, '[role="alert"]')).toContain('The speech engine is unavailable.');
    expect(el.shadowRoot?.querySelector('.utterance-transcript')).toBeNull();
  });

  it('disables the button while the upload is out', async () => {
    const el = await mount();
    el.sending = true;
    await el.updateComplete;

    expect(button(el).disabled).toBe(true);
    expect(text(el, '.mic-button')).toContain('Sending...');
  });
});
