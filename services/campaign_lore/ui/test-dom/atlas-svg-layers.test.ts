/**
 * Atlas pin and territory layers render as SVG (TASK-0904).
 * The element runs in headless Chromium. The test sets the public `pins` and `territories`
 * properties and reads the rendered shadow DOM, as the browser lays it out.
 * Lit parses an `html` template in the HTML namespace, so SVG children in such a template
 * have no geometry and do not show. Governing ADRs: ADR-0004, ADR-0013.
 */

import { afterEach, describe, expect, it } from 'vitest';
import '../src/runefoble-campaign-atlas.ts';
import type { AtlasPin, AtlasTerritory } from '../src/runefoble-campaign-atlas.ts';

const SVG_NS = 'http://www.w3.org/2000/svg';

const PIN: AtlasPin = {
  pin_id: 'pin-1',
  title: 'Ironford Gate',
  layer: 'continental',
  coordinates: { x: 120, y: 240 },
};

const TERRITORY: AtlasTerritory = {
  territory_id: 'territory-1',
  name: 'Ashen Reach',
  layer: 'continental',
  polygon_coordinates: [[0, 0], [200, 0], [200, 200]],
  owner_faction: 'Ash Court',
  is_contested: false,
};

type Atlas = HTMLElement & {
  pins: AtlasPin[];
  territories: AtlasTerritory[];
  updateComplete: Promise<boolean>;
};

async function mount(): Promise<Atlas> {
  const el = document.createElement('runefoble-campaign-atlas') as Atlas;
  el.pins = [PIN];
  el.territories = [TERRITORY];
  document.body.append(el);
  await el.updateComplete;
  return el;
}

describe('runefoble-campaign-atlas SVG layers (TASK-0904)', () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders a pin as an SVG text element with the pin label', async () => {
    const el = await mount();

    const label = el.shadowRoot!.querySelector('[data-pin-id="pin-1"] text.pin-label') as SVGTextElement;

    expect(label).not.toBeNull();
    expect(label.namespaceURI).toBe(SVG_NS);
    expect(label.textContent).toBe('Ironford Gate');
    expect(label.getBBox().width).toBeGreaterThan(0);
  });

  it('renders a territory as an SVG polygon with geometry', async () => {
    const el = await mount();

    const polygon = el.shadowRoot!.querySelector('[data-territory-id="territory-1"]') as SVGPolygonElement;

    expect(polygon).not.toBeNull();
    expect(polygon.namespaceURI).toBe(SVG_NS);
    expect(polygon.getBBox().width).toBe(200);
  });
});
