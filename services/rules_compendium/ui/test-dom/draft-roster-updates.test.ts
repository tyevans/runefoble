/**
 * Draft roster changes replace entries (TASK-0908, ADR-0004).
 * `<runefoble-rules-compendium>` passes its draft list to `<runefoble-encounter-builder>`.
 * A count change in either element must put a new entry in a new list. It must never change
 * an entry that the other element still holds. The test reads the rendered tab count.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/runefoble-rules-compendium.ts';
import '../src/runefoble-encounter-builder.ts';
import type { DraftMonsterEntry } from '../src/types.ts';

type Builder = HTMLElement & {
  updateComplete: Promise<boolean>;
  draftMonsters: DraftMonsterEntry[];
  addMonster(m: DraftMonsterEntry): void;
  removeMonster(name: string): void;
};
type Compendium = HTMLElement & { updateComplete: Promise<boolean>; draftMonsters: DraftMonsterEntry[] };

const goblin = (count: number): DraftMonsterEntry => ({ name: 'Goblin', cr: 0.25, xp: 50, role: 'skirmisher', count });

afterEach(() => {
  document.querySelectorAll('runefoble-encounter-builder, runefoble-rules-compendium').forEach((el) => el.remove());
});

describe('draft roster updates', () => {
  it('addMonster and removeMonster put new entries and leave the old entry unchanged', async () => {
    const el = document.createElement('runefoble-encounter-builder') as Builder;
    const entry = goblin(1);
    el.draftMonsters = [entry];
    document.body.append(el);
    await el.updateComplete;

    el.addMonster(goblin(1));
    expect(el.draftMonsters[0]).not.toBe(entry);
    expect(el.draftMonsters[0].count).toBe(2);
    expect(entry.count).toBe(1);

    const added = el.draftMonsters[0];
    el.removeMonster('Goblin');
    expect(el.draftMonsters[0]).not.toBe(added);
    expect(el.draftMonsters[0].count).toBe(1);
    expect(added.count).toBe(2);
  });

  it('a monster added from the lookup updates the tab count with a new entry', async () => {
    const el = document.createElement('runefoble-rules-compendium') as Compendium;
    const entry = goblin(1);
    el.draftMonsters = [entry];
    document.body.append(el);
    await el.updateComplete;

    const lookup = el.shadowRoot?.querySelector('runefoble-rules-lookup');
    if (!lookup) throw new Error('No rules lookup on the search tab');
    lookup.dispatchEvent(new CustomEvent('monster-added', { detail: { monster: goblin(1) } }));
    await el.updateComplete;

    expect(el.draftMonsters[0]).not.toBe(entry);
    expect(entry.count).toBe(1);
    expect(el.shadowRoot?.textContent).toContain('CR Builder (2)');
  });
});
