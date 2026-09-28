/**
 * Frontend Component Test Suite for Mobile Minigames Suite.
 *
 * TASK-0261: Mobile-First Touch-Optimized Tavern and Casino Minigames Suite
 * Governing ADRs: ADR-0004, ADR-0006, ADR-0012
 * Product & Stories: PRD-0024, US-0074
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..');

const DARTS_PATH = resolve(FRONTEND_DIR, 'src/components/minigames/runefoble-minigame-darts.ts');
const LIARS_DICE_PATH = resolve(FRONTEND_DIR, 'src/components/minigames/runefoble-minigame-liars-dice.ts');
const ROULETTE_PATH = resolve(FRONTEND_DIR, 'src/components/minigames/runefoble-minigame-roulette.ts');
const STORIES_PATH = resolve(FRONTEND_DIR, 'src/stories/runefoble-minigames.stories.ts');

describe('TASK-0261: Mobile-First Minigames Suite Components', () => {
  it('runefoble-minigame-darts.ts exists and satisfies < 300 lines limit', () => {
    assert.ok(existsSync(DARTS_PATH), 'Darts component file must exist');
    const content = readFileSync(DARTS_PATH, 'utf-8');
    const lineCount = content.split('\n').length;
    assert.ok(lineCount < 300, `Darts component must be < 300 lines, got ${lineCount}`);
    assert.ok(content.includes("@customElement('runefoble-minigame-darts')"));
    assert.ok(content.includes('dart-thrown'));
    assert.ok(content.includes('handleTouchStart'));
    assert.ok(content.includes('handleTouchEnd'));
    assert.ok(content.includes('navigator.vibrate'));
  });

  it('runefoble-minigame-liars-dice.ts exists and satisfies < 280 lines limit', () => {
    assert.ok(existsSync(LIARS_DICE_PATH), 'Liars Dice component file must exist');
    const content = readFileSync(LIARS_DICE_PATH, 'utf-8');
    const lineCount = content.split('\n').length;
    assert.ok(lineCount < 280, `Liars Dice component must be < 280 lines, got ${lineCount}`);
    assert.ok(content.includes("@customElement('runefoble-minigame-liars-dice')"));
    assert.ok(content.includes('shakeCup'));
    assert.ok(content.includes('peek-shade'));
    assert.ok(content.includes('bid-placed'));
    assert.ok(content.includes('liar-called'));
    assert.ok(content.includes('navigator.vibrate'));
  });

  it('runefoble-minigame-roulette.ts exists and satisfies < 280 lines limit', () => {
    assert.ok(existsSync(ROULETTE_PATH), 'Roulette component file must exist');
    const content = readFileSync(ROULETTE_PATH, 'utf-8');
    const lineCount = content.split('\n').length;
    assert.ok(lineCount < 280, `Roulette component must be < 280 lines, got ${lineCount}`);
    assert.ok(content.includes("@customElement('runefoble-minigame-roulette')"));
    assert.ok(content.includes('placeBet'));
    assert.ok(content.includes('spinWheel'));
    assert.ok(content.includes('wheel-spun'));
    assert.ok(content.includes('felt-table'));
    assert.ok(content.includes('token-chip'));
  });

  it('runefoble-minigames.stories.ts exists and defines mobile viewport light and dark stories', () => {
    assert.ok(existsSync(STORIES_PATH), 'Stories file must exist');
    const content = readFileSync(STORIES_PATH, 'utf-8');
    assert.ok(content.includes('Darts501Light'));
    assert.ok(content.includes('Darts501Dark'));
    assert.ok(content.includes('LiarsDiceLight'));
    assert.ok(content.includes('LiarsDiceDark'));
    assert.ok(content.includes('RouletteLight'));
    assert.ok(content.includes('RouletteDark'));
    assert.ok(content.includes('375px'), 'Stories must provide 375px mobile viewport frame');
  });
});
