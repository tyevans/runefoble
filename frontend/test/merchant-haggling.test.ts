/**
 * Unit tests for Merchant Haggler and DM Negotiation Drawer components.
 * TASK-0262: Interactive Merchant Haggling Engine with DM Arbitration Controls
 * Governed by ADR-0001, ADR-0004, ADR-0006, ADR-0012.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ROOT_DIR = resolve(process.cwd());
const HAGGLER_PATH = resolve(ROOT_DIR, 'src/components/minigames/runefoble-merchant-haggler.ts');
const HAGGLER_STYLES_PATH = resolve(ROOT_DIR, 'src/components/minigames/runefoble-merchant-haggler.styles.ts');
const DM_DRAWER_PATH = resolve(ROOT_DIR, 'src/components/dm-controls/runefoble-dm-negotiation-drawer.ts');
const DM_DRAWER_STYLES_PATH = resolve(ROOT_DIR, 'src/components/dm-controls/runefoble-dm-negotiation-drawer.styles.ts');
const HAGGLER_STORIES_PATH = resolve(ROOT_DIR, 'src/stories/runefoble-merchant-haggler.stories.ts');
const DM_DRAWER_STORIES_PATH = resolve(ROOT_DIR, 'src/stories/runefoble-dm-negotiation-drawer.stories.ts');

describe('Merchant Haggling Component Contracts (TASK-0262)', () => {
  it('runefoble-merchant-haggler.ts exists and satisfies file length limit (<400 lines)', () => {
    const content = readFileSync(HAGGLER_PATH, 'utf-8');
    const lines = content.split('\n');
    assert.ok(lines.length < 400, `Haggler file has ${lines.length} lines, must be < 400`);
    assert.ok(content.includes("@customElement('runefoble-merchant-haggler')"));
    assert.ok(content.includes('class RunefobleMerchantHaggler extends LitElement'));
  });

  it('merchant haggler declares required properties, gambits, and events', () => {
    const content = readFileSync(HAGGLER_PATH, 'utf-8');
    assert.ok(content.includes('negotiationId'));
    assert.ok(content.includes('merchantName'));
    assert.ok(content.includes('patience'));
    assert.ok(content.includes('originalPrice'));
    assert.ok(content.includes('counterPrice'));
    assert.ok(content.includes('currentOffer'));
    assert.ok(content.includes('lastVoiceBark'));
    assert.ok(content.includes('flattery'));
    assert.ok(content.includes('bulk_order_promise'));
    assert.ok(content.includes('point_out_flaw'));
    assert.ok(content.includes('hard_intimidation'));
    assert.ok(content.includes('walk_away_bluff'));
    assert.ok(content.includes("new CustomEvent('gambit-executed'"));
    assert.ok(content.includes("new CustomEvent('offer-accepted'"));
  });

  it('runefoble-dm-negotiation-drawer.ts exists and satisfies file length limit (<400 lines)', () => {
    const content = readFileSync(DM_DRAWER_PATH, 'utf-8');
    const lines = content.split('\n');
    assert.ok(lines.length < 400, `DM drawer file has ${lines.length} lines, must be < 400`);
    assert.ok(content.includes("@customElement('runefoble-dm-negotiation-drawer')"));
    assert.ok(content.includes('class RunefobleDMNegotiationDrawer extends LitElement'));
  });

  it('DM drawer contains all four required one-click mood modifiers and custom bark injection', () => {
    const content = readFileSync(DM_DRAWER_PATH, 'utf-8');
    assert.ok(content.includes('soothe_merchant'));
    assert.ok(content.includes('enrage_merchant'));
    assert.ok(content.includes('accept_deal'));
    assert.ok(content.includes('refuse_kick_out'));
    assert.ok(content.includes('bark-input'));
    assert.ok(content.includes('price-override-input'));
    assert.ok(content.includes("new CustomEvent('dm-override'"));
  });

  it('Storybook stories exist for haggler and DM drawer across dark and light themes', () => {
    const hagglerStories = readFileSync(HAGGLER_STORIES_PATH, 'utf-8');
    assert.ok(hagglerStories.includes("title: 'Minigames/RunefobleMerchantHaggler'"));
    assert.ok(hagglerStories.includes('ActiveNegotiationLight'));
    assert.ok(hagglerStories.includes('ActiveNegotiationDark'));

    const dmStories = readFileSync(DM_DRAWER_STORIES_PATH, 'utf-8');
    assert.ok(dmStories.includes("title: 'DMControls/RunefobleDMNegotiationDrawer'"));
    assert.ok(dmStories.includes('LiveArbitrationLight'));
    assert.ok(dmStories.includes('LiveArbitrationDark'));
  });
});
