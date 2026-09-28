import { svg, type SVGTemplateResult } from 'lit';

export function renderBauhausGlyph(icon: string): SVGTemplateResult {
  switch (icon) {
    case 'attack':
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M19.7 4.3a1 1 0 0 0-1.4 0l-9.9 9.9-2.8-2.8a1 1 0 0 0-1.4 1.4l2.8 2.8-3.7 3.7a1 1 0 0 0 1.4 1.4l3.7-3.7 2.8 2.8a1 1 0 0 0 1.4-1.4l-2.8-2.8 9.9-9.9a1 1 0 0 0 0-1.4z" />
          <polygon points="19,3 21,5 15,11 13,9" />
        </svg>
      `;
    case 'dash':
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <polygon points="13,2 4,14 11,14 9,22 20,10 13,10" />
        </svg>
      `;
    case 'disengage':
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M9 6l-5 5 5 5V13h8a4 4 0 0 1 4 4v3h2v-3a6 6 0 0 0-6-6H9V6z" />
          <circle cx="18" cy="7" r="2.5" />
        </svg>
      `;
    case 'dodge':
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M12 2L4 5v6.5C4 16.8 7.4 21.6 12 23c4.6-1.4 8-6.2 8-11.5V5l-8-3zm0 2.2l6 2.3v5.2c0 4.1-2.6 8-6 9.3-3.4-1.3-6-5.2-6-9.3V6.5l6-2.3z" />
          <polygon points="12,6 16,9 12,18 8,9" />
        </svg>
      `;
    case 'cast':
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M12 2l2.4 6.9L21.3 10l-5.3 4.6 1.7 7.1-5.7-3.6-5.7 3.6 1.7-7.1-5.3-4.6 6.9-1.1L12 2z" />
        </svg>
      `;
    default:
      return svg`<circle cx="12" cy="12" r="6" fill="currentColor" />`;
  }
}
