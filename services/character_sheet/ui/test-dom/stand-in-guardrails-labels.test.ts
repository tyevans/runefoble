/**
 * Stand-in guardrail controls carry accessible names (TASK-0650).
 * The e2e suite finds each control by the label in the feature text, so each name must be exact.
 * Governing ADRs: ADR-0004, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import '../src/runefoble-stand-in-guardrails.ts';

async function mountGuardrails() {
  const el = document.createElement('runefoble-stand-in-guardrails') as HTMLElement & {
    avoidMelee: boolean;
    riskThreshold: string;
    updateComplete: Promise<boolean>;
  };
  // Start from the opposite of the values that the test picks.
  el.avoidMelee = false;
  el.riskThreshold = 'reckless';
  document.body.append(el);
  await el.updateComplete;
  return el;
}

afterEach(() => {
  document.querySelectorAll('runefoble-stand-in-guardrails').forEach((el) => el.remove());
});

describe('runefoble-stand-in-guardrails labels', () => {
  it('saves avoid_melee when the user checks the "Avoid Melee" toggle and picks a risk appetite', async () => {
    const el = await mountGuardrails();
    const saved = new Promise<Record<string, unknown>>((resolve) => {
      el.addEventListener('guardrails-saved', (e) => resolve((e as CustomEvent).detail), { once: true });
    });

    await page.getByRole('combobox', { name: 'Risk Appetite', exact: true }).selectOptions('cautious');
    await page.getByRole('checkbox', { name: 'Avoid Melee', exact: true }).click();
    await page.getByRole('button', { name: 'Save Tactical Guardrails', exact: true }).click();

    const detail = await saved;
    expect(detail.avoid_melee).toBe(true);
    expect(detail.risk_threshold).toBe('cautious');
  });

  it('names the permadeath toggle by its own label', async () => {
    await mountGuardrails();

    await expect
      .element(page.getByRole('checkbox', { name: 'Permadeath Safeguard (Zero-HP Stabilization)', exact: true }))
      .toBeInTheDocument();
  });
});
