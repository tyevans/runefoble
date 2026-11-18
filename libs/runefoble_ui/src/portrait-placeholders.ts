/**
 * Bauhaus geometric portrait placeholders for character presets.
 *
 * Each portrait is an inline SVG data URI. Storybook and the App Shell do not
 * serve a static portrait directory, so inline data is the only asset source
 * that always resolves. Colours are the flat Bauhaus accents from
 * docs/reference/design-tokens-and-themes.md (an SVG data URI cannot read CSS
 * custom properties).
 */

const INK = '#121212';
const CANVAS = '#f8f9fa';
const RED = '#e63946';
const BLUE = '#1d3557';
const YELLOW = '#ffb703';

interface PortraitShapes {
  readonly background: string;
  readonly body: string;
  readonly head: string;
}

const SHAPES: Record<'fighter' | 'wizard' | 'cleric' | 'rogue' | 'paladin', PortraitShapes> = {
  fighter: { background: RED, body: INK, head: CANVAS },
  wizard: { background: BLUE, body: YELLOW, head: CANVAS },
  cleric: { background: YELLOW, body: BLUE, head: CANVAS },
  rogue: { background: INK, body: RED, head: YELLOW },
  paladin: { background: CANVAS, body: BLUE, head: RED },
};

export type PortraitPlaceholderId = keyof typeof SHAPES;

function portraitMarkup({ background, body, head }: PortraitShapes): string {
  return [
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">',
    `<rect width="120" height="120" fill="${background}"/>`,
    `<rect x="20" y="78" width="80" height="34" fill="${body}" stroke="${INK}" stroke-width="4"/>`,
    `<circle cx="60" cy="48" r="22" fill="${head}" stroke="${INK}" stroke-width="4"/>`,
    '</svg>',
  ].join('');
}

function toDataUri(markup: string): string {
  return `data:image/svg+xml,${encodeURIComponent(markup)}`;
}

export const PORTRAIT_PLACEHOLDERS: Record<PortraitPlaceholderId, string> = {
  fighter: toDataUri(portraitMarkup(SHAPES.fighter)),
  wizard: toDataUri(portraitMarkup(SHAPES.wizard)),
  cleric: toDataUri(portraitMarkup(SHAPES.cleric)),
  rogue: toDataUri(portraitMarkup(SHAPES.rogue)),
  paladin: toDataUri(portraitMarkup(SHAPES.paladin)),
};
