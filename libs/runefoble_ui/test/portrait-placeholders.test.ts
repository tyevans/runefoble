import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { PORTRAIT_PLACEHOLDERS, type PortraitPlaceholderId } from '../src/portrait-placeholders.ts';

const IDS: PortraitPlaceholderId[] = ['fighter', 'wizard', 'cleric', 'rogue', 'paladin'];

describe('PORTRAIT_PLACEHOLDERS', () => {
  it('provides a self-contained SVG data URI for every portrait preset', () => {
    for (const id of IDS) {
      const url = PORTRAIT_PLACEHOLDERS[id];
      assert.ok(url.startsWith('data:image/svg+xml,'), `${id} is not an SVG data URI`);
      const markup = decodeURIComponent(url.slice('data:image/svg+xml,'.length));
      assert.match(markup, /^<svg [^>]*xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
      assert.match(markup, /viewBox="0 0 \d+ \d+"/);
    }
  });

  it('gives each preset a distinct image', () => {
    const urls = new Set(IDS.map((id) => PORTRAIT_PLACEHOLDERS[id]));
    assert.equal(urls.size, IDS.length);
  });
});
