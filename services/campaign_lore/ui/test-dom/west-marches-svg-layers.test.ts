/**
 * West Marches pin and fog layers render as SVG (TASK-0904).
 * The elements run in headless Chromium. The test sets public properties and reads the
 * rendered shadow DOM. Governing ADRs: ADR-0004, ADR-0013.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/west_marches/discovery_pin_layer.ts';
import '../src/west_marches/frontier_hex_overlay.ts';
import type { WestMarchesDiscovery, WestMarchesOutpost } from '../src/west_marches/types.ts';

const SVG_NS = 'http://www.w3.org/2000/svg';

const DISCOVERY: WestMarchesDiscovery = {
  discovery_id: 'discovery-1',
  name: 'Sunken Shrine',
  discovery_type: 'ruin',
  coordinates: { x: 300, y: 400 },
  discovered_by_campaign_id: 'campaign-1',
  discovered_by_party_name: 'Party Blue',
};

const OUTPOST: WestMarchesOutpost = {
  outpost_id: 'outpost-1',
  name: 'Ironford',
  region: 'north',
  level: 1,
  facilities: {},
  contributing_campaigns: [],
};

type Lit = HTMLElement & { updateComplete: Promise<boolean> };

async function mount<T extends Lit>(tag: string, setup: (el: T) => void): Promise<T> {
  const el = document.createElement(tag) as T;
  setup(el);
  document.body.append(el);
  await el.updateComplete;
  return el;
}

describe('West Marches SVG layers (TASK-0904)', () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders discovery and outpost labels as SVG text elements', async () => {
    const el = await mount<Lit & { discoveries: WestMarchesDiscovery[]; outposts: WestMarchesOutpost[] }>(
      'runefoble-discovery-pin-layer',
      (layer) => {
        layer.discoveries = [DISCOVERY];
        layer.outposts = [OUTPOST];
      },
    );

    const labels = [...el.shadowRoot!.querySelectorAll('text.pin-tag')] as SVGTextElement[];

    expect(labels.map((label) => label.textContent?.trim())).toEqual(['🏰 Ironford', 'Sunken Shrine']);
    for (const label of labels) {
      expect(label.namespaceURI).toBe(SVG_NS);
      expect(label.getBBox().width).toBeGreaterThan(0);
    }
  });

  it('renders the fog boundaries as SVG polygons with geometry', async () => {
    const el = await mount<Lit>('runefoble-frontier-hex-overlay', () => {});

    const fog = el.shadowRoot!.querySelector('polygon.fog-boundary') as SVGPolygonElement;

    expect(fog).not.toBeNull();
    expect(fog.namespaceURI).toBe(SVG_NS);
    expect(fog.getBBox().width).toBe(350);
  });
});
