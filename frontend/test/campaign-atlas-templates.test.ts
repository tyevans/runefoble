/**
 * Unit & Integration tests for Campaign Atlas Layers and Pins Subviews Modular Decomposition.
 * TASK-0196: Campaign Atlas Layers and Pins Subviews Modular Decomposition
 * ADR-0004, ADR-0007, ADR-0012, ADR-0013
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// Template & types imports
import {
  type AtlasPin,
  type AtlasTerritory,
  type CodexEntry,
  filterVisibleTerritories,
  renderTerritoryDefs,
  renderTerritories,
  filterVisiblePins,
  calculateCanvasCoordinates,
  renderPinsLayer,
  renderCodexSidebar,
} from '../../services/campaign_lore/ui/src/atlas/index.ts';

const sampleTerritories: AtlasTerritory[] = [
  {
    territory_id: 'terr-1',
    name: 'Silverkeep Garrison',
    layer: 'continental',
    polygon_coordinates: [[150, 150], [450, 150], [450, 450], [150, 450]],
    owner_faction: 'Silverguard Alliance',
    is_contested: false,
    era: 'Session 12: Liberation',
    metadata: { banner_color: '#4361ee' },
  },
  {
    territory_id: 'terr-2',
    name: 'Obsidian Borderlands',
    layer: 'regional',
    polygon_coordinates: [[450, 200], [750, 200], [700, 500], [450, 450]],
    owner_faction: 'Disputed',
    is_contested: true,
    era: 'Age of Rebirth',
    metadata: { banner_color: '#d90429' },
  },
];

const samplePins: AtlasPin[] = [
  {
    pin_id: 'pin-1',
    title: 'Garrison Fortress Breach',
    layer: 'continental',
    coordinates: { x: 300, y: 300 },
    description: 'Where the party breached western gates.',
    era: 'Session 12',
  },
  {
    pin_id: 'pin-2',
    title: 'Sunken Vault of Runes',
    layer: 'regional',
    coordinates: { x: 600, y: 350 },
    description: 'Ancient subterranean laboratory discovered.',
    era: 'Session 14',
  },
];

const sampleCodex: CodexEntry[] = [
  {
    entry_id: 'codex-1',
    title: 'Observations on the Obsidian Veil',
    content: 'Cabal operatives have established shadow conduits beneath the garrison.',
    privacy: 'private',
    author_id: 'rowan',
    linked_entities: [{ id: 'ent-1', name: 'Order of the Obsidian Veil', entity_type: 'faction' }],
  },
  {
    entry_id: 'codex-2',
    title: 'Silverkeep Defense Log',
    content: 'Allied forces reinforced the perimeter following the siege.',
    privacy: 'party_shared',
    author_id: 'valeros',
    linked_entities: [{ id: 'ent-2', name: 'Silverkeep Garrison', entity_type: 'location' }],
  },
];

describe('Atlas Subview: Territory Renderer', () => {
  it('filters visible territories by layer and contested flag', () => {
    // Continental layer includes 'continental'
    const continental = filterVisibleTerritories(sampleTerritories, 'continental', undefined, false);
    assert.equal(continental.length, 1);
    assert.equal(continental[0].territory_id, 'terr-1');

    // Regional layer includes both 'regional' and 'continental' fallback
    const regional = filterVisibleTerritories(sampleTerritories, 'regional', undefined, false);
    assert.equal(regional.length, 2);

    // Contested filter only returns contested territories
    const contestedOnly = filterVisibleTerritories(sampleTerritories, 'regional', undefined, true);
    assert.equal(contestedOnly.length, 1);
    assert.equal(contestedOnly[0].territory_id, 'terr-2');
  });

  it('filters territories by era timeline matching', () => {
    const eraFiltered = filterVisibleTerritories(sampleTerritories, 'regional', 'Rebirth', false);
    assert.equal(eraFiltered.length, 1);
    assert.equal(eraFiltered[0].territory_id, 'terr-2');
  });

  it('renders territory defs and polygons template results', () => {
    const defs = renderTerritoryDefs();
    assert.ok(defs);

    const template = renderTerritories({
      territories: sampleTerritories,
      activeLayer: 'regional',
      showContestedOnly: false,
    });
    assert.ok(template);
  });
});

describe('Atlas Subview: Pins Layer', () => {
  it('filters pins by layer and chronological era', () => {
    const continentalPins = filterVisiblePins(samplePins, 'continental', undefined);
    assert.equal(continentalPins.length, 1);
    assert.equal(continentalPins[0].pin_id, 'pin-1');

    const regionalPins = filterVisiblePins(samplePins, 'regional', undefined);
    assert.equal(regionalPins.length, 2);

    const eraPins = filterVisiblePins(samplePins, 'regional', '14');
    assert.equal(eraPins.length, 1);
    assert.equal(eraPins[0].pin_id, 'pin-2');
  });

  it('calculates canvas coordinates correctly accounting for pan and zoom', () => {
    const mockEvent = {
      clientX: 250,
      clientY: 300,
      currentTarget: {
        getBoundingClientRect: () => ({ left: 50, top: 100 }),
      },
    } as unknown as MouseEvent;

    // clientX - left = 200, clientY - top = 200.
    // panX = 50, panY = 50. raw = (200 - 50) / 1.5 = 100.
    const coords = calculateCanvasCoordinates(mockEvent, 50, 50, 1.5);
    assert.equal(coords.x, 100);
    assert.equal(coords.y, 100);
  });

  it('renders pins layer template with selected pin', () => {
    let clickedPin: AtlasPin | null = null;
    const template = renderPinsLayer({
      pins: samplePins,
      activeLayer: 'continental',
      selectedPinId: 'pin-1',
      onPinClick: (p) => {
        clickedPin = p;
      },
    });
    assert.ok(template);
  });
});

describe('Atlas Subview: Codex Sidebar', () => {
  it('renders living codex sidebar with entries and layers', () => {
    let selectedLayer = '';
    let enteredEra = '';
    let selectedEntry: CodexEntry | null = null;

    const template = renderCodexSidebar({
      codexEntries: sampleCodex,
      activeLayer: 'continental',
      activeEra: '',
      selectedEntryId: 'codex-1',
      onSelectLayer: (l) => {
        selectedLayer = l;
      },
      onEraInput: (e) => {
        enteredEra = e;
      },
      onSelectEntry: (ent) => {
        selectedEntry = ent;
      },
    });
    assert.ok(template);
  });
});

describe('Atlas Architecture: File Length Invariants (Hard Invariant 6)', () => {
  it('verifies runefoble-campaign-atlas.ts is strictly < 120 lines', () => {
    const filePath = resolve(
      __dirname,
      '../../services/campaign_lore/ui/src/runefoble-campaign-atlas.ts'
    );
    const content = readFileSync(filePath, 'utf-8');
    const lineCount = content.split('\n').length;
    assert.ok(
      lineCount < 120,
      `runefoble-campaign-atlas.ts has ${lineCount} lines, expected < 120`
    );
  });

  it('verifies all subview templates under src/atlas/ are strictly < 120 lines', () => {
    const atlasDir = resolve(
      __dirname,
      '../../services/campaign_lore/ui/src/atlas'
    );
    const files = [
      'territory-renderer.template.ts',
      'pins-layer.template.ts',
      'codex-sidebar.template.ts',
      'types.ts',
      'index.ts',
    ];

    for (const file of files) {
      const filePath = resolve(atlasDir, file);
      const content = readFileSync(filePath, 'utf-8');
      const lineCount = content.split('\n').length;
      assert.ok(
        lineCount < 120,
        `${file} has ${lineCount} lines, expected < 120`
      );
    }
  });

  it('verifies runefoble-campaign-atlas exports customElement definition and types', () => {
    const filePath = resolve(
      __dirname,
      '../../services/campaign_lore/ui/src/runefoble-campaign-atlas.ts'
    );
    const content = readFileSync(filePath, 'utf-8');
    assert.ok(content.includes("@customElement('runefoble-campaign-atlas')"));
    assert.ok(content.includes('export class RunefobleCampaignAtlas'));
    assert.ok(content.includes('export type { AtlasPin, AtlasTerritory, CodexEntry }'));
  });
});
