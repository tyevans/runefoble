import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { mapUploaderStyles } from './runefoble-map-uploader.styles.ts';

export interface MapUploadedDetail {
  assetId: string;
  downloadUrl: string;
  filename: string;
  byteSize: number;
  contentType: string;
  resolution: { width: number; height: number };
  gridConfig: { cols: number; rows: number; opacity: number };
  shroudConfig: { enabled: boolean; opacity: number };
}

@customElement('runefoble-map-uploader')
export class RunefobleMapUploader extends LitElement {
  static styles = mapUploaderStyles;

  @property({ type: String }) uploadEndpoint = '/api/v1/assets/upload';
  @property({ type: String }) ownerId = 'gm-host';
  @property({ type: String }) assetType = 'battlemap';
  @property({ type: Number }) gridCols = 10;
  @property({ type: Number }) gridRows = 10;
  @property({ type: Number }) gridOpacity = 0.5;
  @property({ type: Number }) shroudOpacity = 0.75;
  @property({ type: Boolean }) shroudEnabled = true;
  @property({ type: String }) previewUrl: string | null = null;
  @property({ type: String }) assetId: string | null = null;
  @property({ type: Boolean }) isUploading = false;
  @property({ type: Number }) uploadProgress = 0;

  @state() private isDragging = false;
  @state() private errorMessage: string | null = null;
  @state() private successMessage: string | null = null;
  @state() private mapResolution: { width: number; height: number } = { width: 1920, height: 1080 };
  @state() private revealedCells: Set<string> = new Set();

  private handleDragOver(e: DragEvent) {
    e.preventDefault();
    this.isDragging = true;
  }

  private handleDragLeave(e: DragEvent) {
    e.preventDefault();
    this.isDragging = false;
  }

  private handleDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging = false;
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      this.uploadFile(e.dataTransfer.files[0]);
    }
  }

  private handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFile(input.files[0]);
    }
  }

  private async uploadFile(file: File) {
    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'Selected file must be an image (PNG, JPEG, WebP, SVG).';
      return;
    }

    this.errorMessage = null;
    this.successMessage = null;
    this.isUploading = true;
    this.uploadProgress = 15;

    // Load preview and determine natural resolution
    const localUrl = URL.createObjectURL(file);
    const img = new Image();
    img.src = localUrl;
    img.onload = () => {
      this.mapResolution = { width: img.naturalWidth || 1920, height: img.naturalHeight || 1080 };
    };
    this.previewUrl = localUrl;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('owner_id', this.ownerId);
    formData.append('asset_type', this.assetType);

    try {
      this.uploadProgress = 50;
      const response = await fetch(this.uploadEndpoint, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      this.uploadProgress = 100;
      const data = await response.json();
      this.assetId = data.asset_id;
      this.successMessage = 'Tactical battlemap uploaded to Silo S3!';

      this.dispatchEvent(
        new CustomEvent<MapUploadedDetail>('map-uploaded', {
          bubbles: true,
          composed: true,
          detail: {
            assetId: data.asset_id,
            downloadUrl: data.download_url || localUrl,
            filename: file.name,
            byteSize: data.byte_size || file.size,
            contentType: data.content_type || file.type,
            resolution: this.mapResolution,
            gridConfig: { cols: this.gridCols, rows: this.gridRows, opacity: this.gridOpacity },
            shroudConfig: { enabled: this.shroudEnabled, opacity: this.shroudOpacity },
          },
        })
      );
    } catch (err) {
      this.errorMessage = err instanceof Error ? err.message : 'Failed to upload battlemap.';
    } finally {
      this.isUploading = false;
    }
  }

  private toggleCellShroud(x: number, y: number) {
    const key = `${x},${y}`;
    const next = new Set(this.revealedCells);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    this.revealedCells = next;
  }

  private revealAll() {
    const all = new Set<string>();
    for (let y = 0; y < this.gridRows; y++) {
      for (let x = 0; x < this.gridCols; x++) {
        all.add(`${x},${y}`);
      }
    }
    this.revealedCells = all;
  }

  private shroudAll() {
    this.revealedCells = new Set();
  }

  private resetMap() {
    this.previewUrl = null;
    this.assetId = null;
    this.revealedCells = new Set();
    this.errorMessage = null;
    this.successMessage = null;
  }

  render() {
    return html`
      <div class="header">
        <div class="title">
          <span>🗺️ Silo S3 Battlemap & Shroud</span>
        </div>
        <div class="actions-bar">
          ${this.previewUrl
            ? html`
                <button class="btn btn-danger" @click="${this.resetMap}">Clear Map</button>
              `
            : ''}
        </div>
      </div>

      ${this.errorMessage
        ? html`<div class="status-msg error">⚠️ ${this.errorMessage}</div>`
        : ''}
      ${this.successMessage
        ? html`<div class="status-msg success">✅ ${this.successMessage}</div>`
        : ''}

      ${!this.previewUrl && !this.isUploading
        ? html`
            <div
              class="dropzone ${this.isDragging ? 'dragging' : ''}"
              @dragover="${this.handleDragOver}"
              @dragleave="${this.handleDragLeave}"
              @drop="${this.handleDrop}"
              @click="${() => this.shadowRoot?.querySelector<HTMLInputElement>('#file-input')?.click()}"
            >
              <span class="drop-icon">📤</span>
              <div class="drop-title">Drag & Drop Tactical Battlemap Here</div>
              <div class="drop-hint">PNG, JPEG, WebP, or SVG (Up to 50MB) • Uploads to Silo S3</div>
              <input
                id="file-input"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                style="display: none;"
                @change="${this.handleFileChange}"
              />
              <button type="button" class="btn btn-primary" style="margin-top: 8px;">
                Browse Files
              </button>
            </div>
          `
        : ''}

      ${this.isUploading
        ? html`
            <div class="progress-section">
              <div class="progress-header">
                <span>Uploading battlemap to Silo S3...</span>
                <span>${this.uploadProgress}%</span>
              </div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${this.uploadProgress}%"></div>
              </div>
            </div>
          `
        : ''}

      ${this.previewUrl
        ? html`
            <div class="preview-container">
              <img src="${this.previewUrl}" alt="Tactical Battlemap" class="preview-image" />
              <div
                class="shroud-overlay"
                style="grid-template-columns: repeat(${this.gridCols}, 1fr); grid-template-rows: repeat(${this.gridRows}, 1fr); opacity: ${this.shroudEnabled ? this.shroudOpacity : 0};"
              >
                ${Array.from({ length: this.gridCols * this.gridRows }).map((_, idx) => {
                  const x = idx % this.gridCols;
                  const y = Math.floor(idx / this.gridCols);
                  const isRevealed = this.revealedCells.has(`${x},${y}`);
                  return html`
                    <div
                      class="shroud-cell ${isRevealed ? 'revealed' : 'shrouded'}"
                      @click="${() => this.toggleCellShroud(x, y)}"
                      title="Cell (${x}, ${y}) - Click to toggle shroud"
                    ></div>
                  `;
                })}
              </div>
            </div>

            <div class="controls-panel">
              <div class="slider-group">
                <label>
                  <span>Grid Columns</span>
                  <span>${this.gridCols}</span>
                </label>
                <input
                  type="range"
                  min="4"
                  max="32"
                  .value="${String(this.gridCols)}"
                  @input="${(e: Event) =>
                    (this.gridCols = Number((e.target as HTMLInputElement).value))}"
                />
              </div>

              <div class="slider-group">
                <label>
                  <span>Grid Rows</span>
                  <span>${this.gridRows}</span>
                </label>
                <input
                  type="range"
                  min="4"
                  max="32"
                  .value="${String(this.gridRows)}"
                  @input="${(e: Event) =>
                    (this.gridRows = Number((e.target as HTMLInputElement).value))}"
                />
              </div>

              <div class="slider-group">
                <label>
                  <span>Shroud Opacity</span>
                  <span>${Math.round(this.shroudOpacity * 100)}%</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  .value="${String(this.shroudOpacity)}"
                  @input="${(e: Event) =>
                    (this.shroudOpacity = Number((e.target as HTMLInputElement).value))}"
                />
              </div>

              <div style="display: flex; gap: 8px; align-items: flex-end; flex-wrap: wrap;">
                <button
                  class="btn ${this.shroudEnabled ? 'btn-primary' : ''}"
                  @click="${() => (this.shroudEnabled = !this.shroudEnabled)}"
                >
                  Shroud: ${this.shroudEnabled ? 'ON' : 'OFF'}
                </button>
                <button class="btn" @click="${this.revealAll}">Reveal All</button>
                <button class="btn" @click="${this.shroudAll}">Shroud All</button>
              </div>
            </div>
          `
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-map-uploader': RunefobleMapUploader;
  }
}
