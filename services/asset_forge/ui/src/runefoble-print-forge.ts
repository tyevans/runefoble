import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { printForgeStyles } from './runefoble-print-forge.styles.ts';

export type PrintForgeTab = 'tiled-map' | 'standees' | 'stl-tokens';

@customElement('runefoble-print-forge')
export class RunefoblePrintForge extends LitElement {
  static styles = printForgeStyles;

  @property({ type: String })
  campaignId = '';

  @property({ type: String })
  activeTab: PrintForgeTab = 'tiled-map';

  @property({ type: Boolean })
  isExporting = false;

  @state()
  private mapTitle = 'Crypt of the Undying Sun';

  @state()
  private widthCells = 16;

  @state()
  private heightCells = 16;

  @state()
  private pageSize: 'letter' | 'a4' = 'letter';

  @state()
  private standeeName = 'Valeros Fighter';

  @state()
  private standeeHp = 24;

  @state()
  private stlDiameterMm = 28;

  @state()
  private stlCondition = 'Poisoned';

  private handleExportPdf() {
    this.dispatchEvent(
      new CustomEvent('export-print-pdf', {
        detail: {
          title: this.mapTitle,
          width_cells: this.widthCells,
          height_cells: this.heightCells,
          page_size: this.pageSize,
          campaign_id: this.campaignId || undefined,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleExportStandees() {
    this.dispatchEvent(
      new CustomEvent('export-standees', {
        detail: {
          sheet_title: `${this.standeeName} Standees`,
          standees: [{ name: this.standeeName, type: 'pc', hp: this.standeeHp, color: '#2a9d8f' }],
          page_size: this.pageSize,
          campaign_id: this.campaignId || undefined,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleExportStl() {
    this.dispatchEvent(
      new CustomEvent('export-stl-token', {
        detail: {
          diameter_mm: this.stlDiameterMm,
          condition_label: this.stlCondition,
          num_slots: 4,
          campaign_id: this.campaignId || undefined,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private renderTiledMapTab() {
    return html`
      <div class="form-group">
        <label class="form-label">Map Title</label>
        <input
          class="input-field"
          type="text"
          .value=${this.mapTitle}
          @input=${(e: Event) => (this.mapTitle = (e.target as HTMLInputElement).value)}
        />
      </div>
      <div class="row">
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Grid Width (cells)</label>
          <input
            class="input-field"
            type="number"
            min="4"
            max="64"
            .value=${String(this.widthCells)}
            @input=${(e: Event) => (this.widthCells = Number((e.target as HTMLInputElement).value))}
          />
        </div>
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Grid Height (cells)</label>
          <input
            class="input-field"
            type="number"
            min="4"
            max="64"
            .value=${String(this.heightCells)}
            @input=${(e: Event) => (this.heightCells = Number((e.target as HTMLInputElement).value))}
          />
        </div>
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Paper Format</label>
          <select
            class="select-field"
            .value=${this.pageSize}
            @change=${(e: Event) => (this.pageSize = (e.target as HTMLSelectElement).value as 'letter' | 'a4')}
          >
            <option value="letter">Letter (8.5 x 11")</option>
            <option value="a4">A4 (210 x 297mm)</option>
          </select>
        </div>
      </div>
      <button class="action-btn" ?disabled=${this.isExporting} @click=${this.handleExportPdf}>
        ${this.isExporting ? 'Generating PDF...' : 'Export Grid-Calibrated Multi-Page PDF'}
      </button>

      <div class="preview-panel">
        <svg class="preview-svg" viewBox="0 0 240 140">
          <rect x="20" y="10" width="90" height="120" fill="#fdfdfd" stroke="#121212" stroke-width="1.5" />
          <rect x="130" y="10" width="90" height="120" fill="#fdfdfd" stroke="#121212" stroke-width="1.5" />
          <line x1="20" y1="40" x2="110" y2="40" stroke="#cccccc" stroke-dasharray="2,2" />
          <line x1="20" y1="70" x2="110" y2="70" stroke="#cccccc" stroke-dasharray="2,2" />
          <line x1="130" y1="40" x2="220" y2="40" stroke="#cccccc" stroke-dasharray="2,2" />
          <line x1="130" y1="70" x2="220" y2="70" stroke="#cccccc" stroke-dasharray="2,2" />
          <circle cx="20" cy="10" r="3" fill="#e63946" />
          <circle cx="110" cy="130" r="3" fill="#e63946" />
        </svg>
        <div class="preview-stats">
          Tiled Multi-Page Slice: 1-inch physical squares @ 300 DPI.<br />
          Alignment crosshairs & margin cut lines included.
        </div>
      </div>
    `;
  }

  private renderStandeesTab() {
    return html`
      <div class="form-group">
        <label class="form-label">Hero / Monster Name</label>
        <input
          class="input-field"
          type="text"
          .value=${this.standeeName}
          @input=${(e: Event) => (this.standeeName = (e.target as HTMLInputElement).value)}
        />
      </div>
      <div class="row">
        <div class="form-group" style="flex: 1;">
          <label class="form-label">HP Pool</label>
          <input
            class="input-field"
            type="number"
            .value=${String(this.standeeHp)}
            @input=${(e: Event) => (this.standeeHp = Number((e.target as HTMLInputElement).value))}
          />
        </div>
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Paper Size</label>
          <select
            class="select-field"
            .value=${this.pageSize}
            @change=${(e: Event) => (this.pageSize = (e.target as HTMLSelectElement).value as 'letter' | 'a4')}
          >
            <option value="letter">Letter</option>
            <option value="a4">A4</option>
          </select>
        </div>
      </div>
      <button class="action-btn" ?disabled=${this.isExporting} @click=${this.handleExportStandees}>
        ${this.isExporting ? 'Rendering...' : 'Export Foldable Papercraft Standees'}
      </button>

      <div class="preview-panel">
        <svg class="preview-svg" viewBox="0 0 200 120">
          <rect x="60" y="10" width="80" height="100" fill="#f8f9fa" stroke="#121212" stroke-width="1.5" />
          <line x1="60" y1="60" x2="140" y2="60" stroke="#e63946" stroke-width="2" stroke-dasharray="4,3" />
          <text x="100" y="40" font-size="8" text-anchor="middle" fill="#555555">BACK (MIRRORED)</text>
          <text x="100" y="85" font-size="8" text-anchor="middle" fill="#121212" font-weight="bold">FRONT FACE</text>
        </svg>
        <div class="preview-stats">
          Mirrored folding standee sheet with inverted backface artwork and base tabs.
        </div>
      </div>
    `;
  }

  private renderStlTab() {
    return html`
      <div class="row">
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Miniature Base Diameter</label>
          <select
            class="select-field"
            .value=${String(this.stlDiameterMm)}
            @change=${(e: Event) => (this.stlDiameterMm = Number((e.target as HTMLSelectElement).value))}
          >
            <option value="28">28mm (Medium Creature / 1-inch)</option>
            <option value="50">50mm (Large Creature / 2-inch)</option>
          </select>
        </div>
        <div class="form-group" style="flex: 1;">
          <label class="form-label">Snap-In Status Clip</label>
          <select
            class="select-field"
            .value=${this.stlCondition}
            @change=${(e: Event) => (this.stlCondition = (e.target as HTMLSelectElement).value)}
          >
            <option value="Poisoned">Poisoned (Green Clip)</option>
            <option value="Stunned">Stunned (Yellow Clip)</option>
            <option value="Blessed">Blessed (Gold Clip)</option>
            <option value="Blinded">Blinded (Dark Clip)</option>
          </select>
        </div>
      </div>
      <button class="action-btn" ?disabled=${this.isExporting} @click=${this.handleExportStl}>
        ${this.isExporting ? 'Generating Mesh...' : 'Export Watertight 3D STL Mesh'}
      </button>

      <div class="preview-panel">
        <svg class="preview-svg" viewBox="0 0 160 120">
          <circle cx="80" cy="60" r="45" fill="none" stroke="#121212" stroke-width="2" />
          <circle cx="80" cy="60" r="38" fill="#eaeaea" stroke="#888888" stroke-dasharray="3,3" />
          <rect x="76" y="11" width="8" height="8" fill="#e63946" />
          <rect x="76" y="101" width="8" height="8" fill="#e63946" />
          <rect x="31" y="56" width="8" height="8" fill="#e63946" />
          <rect x="121" y="56" width="8" height="8" fill="#e63946" />
        </svg>
        <div class="preview-stats">
          Watertight 2-Manifold Mesh with 4 snap-in status clip slots. Slicer ready.
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="header">
        <span class="title">Printable Tabletop Forge</span>
        <span class="badge">Tactile TTRPG</span>
      </div>

      <div class="tabs">
        <button
          class="tab-btn ${this.activeTab === 'tiled-map' ? 'active' : ''}"
          @click=${() => (this.activeTab = 'tiled-map')}
        >
          Tiled Map PDF
        </button>
        <button
          class="tab-btn ${this.activeTab === 'standees' ? 'active' : ''}"
          @click=${() => (this.activeTab = 'standees')}
        >
          Paper Standees
        </button>
        <button
          class="tab-btn ${this.activeTab === 'stl-tokens' ? 'active' : ''}"
          @click=${() => (this.activeTab = 'stl-tokens')}
        >
          3D STL Tokens
        </button>
      </div>

      ${this.activeTab === 'tiled-map'
        ? this.renderTiledMapTab()
        : this.activeTab === 'standees'
        ? this.renderStandeesTab()
        : this.renderStlTab()}
    `;
  }
}
