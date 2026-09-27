import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

export interface BattlemapItem {
  id: string;
  name: string;
  cols: number;
  rows: number;
  backgroundImageUrl?: string;
  spawnCoords?: [number, number];
}

@customElement('runefoble-map-switcher')
export class RunefobleMapSwitcher extends LitElement {
  static styles = css`
    :host { display: block; font-family: var(--rf-font-family, system-ui, sans-serif); }
    .backdrop {
      position: fixed; inset: 0; background: rgba(0,0,0,0.6);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .modal {
      background: var(--rf-bg-surface, #ffffff); border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a1a1a);
      box-shadow: var(--rf-shadow, 6px 6px 0px #1a1a1a); width: 90%; max-width: 520px; padding: 16px; box-sizing: border-box;
    }
    .header {
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 2px solid var(--rf-border-color, #1a1a1a); padding-bottom: 8px; margin-bottom: 12px;
    }
    .header h3 { margin: 0; font-size: 1.1rem; font-weight: 800; }
    .close-btn { background: none; border: none; font-size: 1.2rem; cursor: pointer; font-weight: 800; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px; }
    .card {
      border: 2px solid var(--rf-border-color, #1a1a1a); padding: 8px; display: flex; flex-direction: column;
      gap: 6px; box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a1a1a); background: var(--rf-bg-surface, #ffffff);
    }
    .card.active { border-color: var(--rf-accent-primary, #e63946); background: #fdf0ed; }
    .thumb { height: 60px; background: #e0e0e0; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; }
    .card-title { font-weight: 800; font-size: 0.8rem; margin: 0; }
    .card-meta { font-size: 0.7rem; color: #555555; }
    .teleport-btn {
      background: var(--rf-border-color, #1a1a1a); color: #ffffff; border: none;
      padding: 4px 6px; font-weight: 700; font-size: 0.7rem; cursor: pointer;
    }
    .teleport-btn:hover { background: var(--rf-accent-primary, #e63946); }
  `;

  @property({ type: Boolean }) open = false;
  @property({ type: String }) currentMapId = '';
  @property({ type: Array }) maps: BattlemapItem[] = [];
  @property({ type: Object }) tokenTeleports: Record<string, [number, number]> = {};

  close() {
    this.open = false;
    this.dispatchEvent(new CustomEvent('switcher-closed', { bubbles: true, composed: true }));
  }

  switchMap(map: BattlemapItem) {
    const teleports = Object.keys(this.tokenTeleports).length > 0
      ? this.tokenTeleports
      : { valeros: map.spawnCoords || [2, 2] };
    const detail = {
      newMapId: map.id,
      cols: map.cols,
      rows: map.rows,
      backgroundImageUrl: map.backgroundImageUrl || '',
      tokenTeleports: teleports,
    };
    this.dispatchEvent(new CustomEvent('map-switched', { bubbles: true, composed: true, detail }));
    this.close();
  }

  render() {
    if (!this.open) return html``;
    return html`
      <div class="backdrop" @click="${this.close}">
        <div class="modal" @click="${(e: Event) => e.stopPropagation()}">
          <div class="header">
            <h3>🗺️ Campaign Battlemaps</h3>
            <button class="close-btn" @click="${this.close}">✕</button>
          </div>
          <div class="grid">
            ${this.maps.map((m) => html`
              <div class="card ${m.id === this.currentMapId ? 'active' : ''}">
                <div class="thumb">🏰</div>
                <div class="card-title">${m.name}</div>
                <div class="card-meta">${m.cols}x${m.rows} grid ${m.id === this.currentMapId ? '• Active' : ''}</div>
                <button class="teleport-btn" @click="${() => this.switchMap(m)}">
                  ⚡ Teleport Here
                </button>
              </div>
            `)}
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-map-switcher': RunefobleMapSwitcher;
  }
}
