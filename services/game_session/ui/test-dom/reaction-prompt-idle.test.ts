/**
 * The reaction prompt opens only for a real reaction (TASK-0939).
 * `<runefoble-combat-reaction-prompt>` runs in headless Chromium. Without reaction data it
 * shows no dialog and starts no countdown. The test reads the rendered DOM and spies on the
 * browser timer, as the App Shell would observe it.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import '../src/runefoble-combat-reaction-prompt.ts';

type Prompt = HTMLElement & { updateComplete: Promise<boolean> };

function dialogOf(el: Prompt): Element | null {
  return el.shadowRoot?.querySelector('[role="dialog"]') ?? null;
}

async function mount(attrs: Record<string, string> = {}): Promise<Prompt> {
  const el = document.createElement('runefoble-combat-reaction-prompt') as Prompt;
  for (const [name, value] of Object.entries(attrs)) el.setAttribute(name, value);
  document.body.append(el);
  await el.updateComplete;
  return el;
}

afterEach(() => {
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe('reaction prompt without reaction data', () => {
  it('renders no dialog and no placeholder combatant name', async () => {
    const el = await mount();

    expect(dialogOf(el)).toBeNull();
    expect(el.shadowRoot?.textContent ?? '').not.toContain('shouted');
    expect(el.shadowRoot?.textContent ?? '').not.toContain('Combatant');
  });

  it('starts no countdown timer when it connects', async () => {
    const setInterval = vi.spyOn(window, 'setInterval');

    await mount();

    expect(setInterval).not.toHaveBeenCalled();
  });

  it('stays closed when only the reaction id is set', async () => {
    const setInterval = vi.spyOn(window, 'setInterval');

    const el = await mount({ reactionId: 'rx-1' });

    expect(dialogOf(el)).toBeNull();
    expect(setInterval).not.toHaveBeenCalled();
  });
});

describe('reaction prompt with reaction data', () => {
  it('opens the dialog and starts the countdown', async () => {
    const setInterval = vi.spyOn(window, 'setInterval');

    const el = await mount({
      reactionId: 'rx-shield-001',
      reactingCombatantId: 'char-marcus',
      reactingCombatantName: 'Marcus (Abjurer)',
      triggerPhrase: 'I cast Shield!',
      reactionType: 'shield',
    });

    expect(dialogOf(el)).not.toBeNull();
    expect(el.shadowRoot?.textContent ?? '').toContain('Marcus (Abjurer) shouted:');
    expect(setInterval).toHaveBeenCalledTimes(1);
  });
});
