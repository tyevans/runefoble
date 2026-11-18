/**
 * Character card portrait element tests (TASK-0797). The card renders in a real Chromium DOM.
 * An empty portrait shows the Bauhaus placeholder for the character's class (TASK-0797).
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { PORTRAIT_PLACEHOLDERS, type PortraitPlaceholderId } from '@runefoble/ui-core';
import '../src/runefoble-character-card.ts';

const CUSTOM_PORTRAIT = 'data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%2F%3E';

async function mountCard(props: { characterClass?: string; portraitUrl?: string }) {
  const el = document.createElement('runefoble-character-card') as HTMLElement & {
    characterClass: string;
    portraitUrl: string;
    updateComplete: Promise<boolean>;
  };
  if (props.characterClass !== undefined) el.characterClass = props.characterClass;
  if (props.portraitUrl !== undefined) el.portraitUrl = props.portraitUrl;
  document.body.append(el);
  await el.updateComplete;
  return el;
}

function portraitSource(el: HTMLElement): string | null {
  return el.shadowRoot?.querySelector('img.char-portrait')?.getAttribute('src') ?? null;
}

afterEach(() => {
  document.querySelectorAll('runefoble-character-card').forEach((el) => el.remove());
});

describe('runefoble-character-card portrait', () => {
  const classes: Array<[string, PortraitPlaceholderId]> = [
    ['Fighter 4', 'fighter'],
    ['Wizard 3', 'wizard'],
    ['Cleric 5', 'cleric'],
    ['Rogue 2', 'rogue'],
    ['Paladin 6', 'paladin'],
  ];

  for (const [characterClass, id] of classes) {
    it(`shows the ${id} placeholder when the portrait is empty`, async () => {
      const el = await mountCard({ characterClass, portraitUrl: '' });

      expect(portraitSource(el)).toBe(PORTRAIT_PLACEHOLDERS[id]);
    });
  }

  it('shows a preset placeholder for a class without its own preset', async () => {
    const el = await mountCard({ characterClass: 'Bard 2', portraitUrl: '' });

    expect(Object.values(PORTRAIT_PLACEHOLDERS)).toContain(portraitSource(el));
  });

  it('shows the given portrait instead of the placeholder when one is set', async () => {
    const el = await mountCard({ characterClass: 'Wizard 3', portraitUrl: CUSTOM_PORTRAIT });

    expect(portraitSource(el)).toBe(CUSTOM_PORTRAIT);
  });
});
