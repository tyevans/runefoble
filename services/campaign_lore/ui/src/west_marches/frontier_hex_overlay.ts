import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { mapStyles } from './styles/map.styles.ts';

export function snapToHexGrid(x: number, y: number, gridSize = 50): { x: number; y: number } {
  return {
    x: Math.round(x / gridSize) * gridSize,
    y: Math.round(y / gridSize) * gridSize,
  };
}

@customElement('runefoble-frontier-hex-overlay')
export class RunefobleFrontierHexOverlay extends LitElement {
  static styles = mapStyles;

  @property({ type: Number }) panX = 0;
  @property({ type: Number }) panY = 0;
  @property({ type: Number }) zoomLevel = 1.0;
  @property({ type: Number }) gridSize = 50;
  @property({ type: Boolean }) showFog = true;

  public snap(x: number, y: number): { x: number; y: number } {
    return snapToHexGrid(x, y, this.gridSize);
  }

  render() {
    return html`
      <svg class="hex-svg" viewBox="0 0 1000 1000">
        <g transform="translate(${this.panX}, ${this.panY}) scale(${this.zoomLevel})">
          <defs>
            <pattern
              id="frontier-hex-grid"
              width="${this.gridSize}"
              height="${this.gridSize}"
              patternUnits="userSpaceOnUse"
            >
              <path d="M ${this.gridSize} 0 L 0 0 0 ${this.gridSize}" fill="none" class="frontier-grid" />
            </pattern>
          </defs>
          <rect width="1000" height="1000" fill="url(#frontier-hex-grid)" />
          ${this.showFog
            ? html`
                <g class="fog-layers">
                  <polygon points="0,0 350,0 280,220 0,300" class="fog-boundary" />
                  <text x="60" y="70" class="fog-text">Uncharted Mists</text>
                  <polygon points="720,620 1000,550 1000,1000 680,1000" class="fog-boundary" />
                  <text x="760" y="800" class="fog-text">Perilous Deep</text>
                </g>
              `
            : ''}
        </g>
      </svg>
    `;
  }
}
