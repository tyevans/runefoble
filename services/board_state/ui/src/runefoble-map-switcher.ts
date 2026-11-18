import { AuthConsumerController } from '@runefoble/ui-core';
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { BoardApiError, postSwitchMap } from './board-api.ts';

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
  private readonly auth = new AuthConsumerController(this);

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
    .error { color: #b00020; font-weight: 700; font-size: 0.8rem; margin-bottom: 8px; }
  `;

  @property({ type: Boolean }) open = false;
  @property({ type: String }) currentMapId = '';
  @property({ type: Array }) maps: BattlemapItem[] = [];
  @property({ type: Object }) tokenTeleports: Record<string, [number, number]> = {};
  /** Board (session) id to switch. Required to teleport. */
  @property({ type: String }) boardId = '';
  @state() private errorMessage = '';
  @state() private busy = false;

  close() {
    this.open = false;
    this.dispatchEvent(new CustomEvent('switcher-closed', { bubbles: true, composed: true }));
  }

  /**
   * POST the switch to the board service. Emits `map-switched` and closes the
   * modal only after a 2xx response. The detail comes from the server response.
   */
  async switchMap(map: BattlemapItem) {
    if (!this.boardId) {
      this.errorMessage = 'No board is open. Map not switched.';
      return;
    }
    const teleports = Object.keys(this.tokenTeleports).length > 0
      ? this.tokenTeleports
      : { valeros: map.spawnCoords || [2, 2] };
    this.busy = true;
    try {
      const result = await postSwitchMap(this.boardId, {
        newMapId: map.id,
        cols: map.cols,
        rows: map.rows,
        backgroundImageUrl: map.backgroundImageUrl || '',
        tokenTeleports: teleports,
      }, { headers: await this.auth.authHeaders() });
      this.errorMessage = '';
      this.dispatchEvent(new CustomEvent('map-switched', {
        bubbles: true,
        composed: true,
        detail: {
          newMapId: result.new_map_id,
          cols: result.cols,
          rows: result.rows,
          backgroundImageUrl: result.background_image_url || '',
          tokenTeleports: result.teleported_tokens,
        },
      }));
      this.close();
    } catch (err) {
      const reason = err instanceof BoardApiError ? err.detail : (err as Error).message;
      this.errorMessage = `Map not switched: ${reason}`;
    } finally {
      this.busy = false;
    }
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
          ${this.errorMessage ? html`<div class="error" role="alert">${this.errorMessage}</div>` : ''}
          <div class="grid">
            ${this.maps.map((m) => html`
              <div class="card ${m.id === this.currentMapId ? 'active' : ''}">
                <div class="thumb">🏰</div>
                <div class="card-title">${m.name}</div>
                <div class="card-meta">${m.cols}x${m.rows} grid ${m.id === this.currentMapId ? '• Active' : ''}</div>
                <button class="teleport-btn" ?disabled="${this.busy}" @click="${() => this.switchMap(m)}">
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
