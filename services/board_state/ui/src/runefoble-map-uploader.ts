import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { mapUploaderStyles } from './runefoble-map-uploader.styles.ts';
import './runefoble-map-dropzone.ts';
import './runefoble-map-grid-config.ts';
import type { DropzoneUploadSuccessDetail } from './runefoble-map-dropzone.ts';
import type { GridConfigDetail } from './runefoble-map-grid-config.ts';

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
  @property({ type: Object }) mapResolution = { width: 1920, height: 1080 };

  @state() private errorMessage: string | null = null;
  @state() private successMessage: string | null = null;
  @state() private revealedCells: Set<string> = new Set();

  resetMap() {
    this.previewUrl = null;
    this.assetId = null;
    this.revealedCells = new Set();
    this.errorMessage = null;
    this.successMessage = null;
    this.isUploading = false;
    this.uploadProgress = 0;
  }

  private handleUploadSuccess(e: CustomEvent<DropzoneUploadSuccessDetail>) {
    const d = e.detail;
    this.assetId = d.assetId;
    this.previewUrl = d.downloadUrl;
    this.mapResolution = d.resolution;
    this.uploadProgress = 100;
    this.isUploading = false;
    this.successMessage = 'Tactical battlemap uploaded to Silo S3!';
    this.dispatchEvent(new CustomEvent<MapUploadedDetail>('map-uploaded', {
      bubbles: true, composed: true,
      detail: {
        assetId: d.assetId, downloadUrl: d.downloadUrl, filename: d.filename,
        byteSize: d.byteSize, contentType: d.contentType, resolution: d.resolution,
        gridConfig: { cols: this.gridCols, rows: this.gridRows, opacity: this.gridOpacity },
        shroudConfig: { enabled: this.shroudEnabled, opacity: this.shroudOpacity },
      },
    }));
  }

  private handleGridChange(e: CustomEvent<GridConfigDetail>) {
    this.gridCols = e.detail.gridCols;
    this.gridRows = e.detail.gridRows;
    this.gridOpacity = e.detail.gridOpacity;
    this.shroudOpacity = e.detail.shroudOpacity;
    this.shroudEnabled = e.detail.shroudEnabled;
    this.revealedCells = e.detail.revealedCells;
  }

  render() {
    return html`
      <div class="header">
        <div class="title"><span>🗺️ Silo S3 Battlemap & Shroud</span></div>
        <div class="actions-bar">
          ${this.previewUrl ? html`<button class="btn btn-danger" @click="${this.resetMap}">Clear Map</button>` : ''}
        </div>
      </div>
      ${this.errorMessage ? html`<div class="status-msg error">⚠️ ${this.errorMessage}</div>` : ''}
      ${this.successMessage ? html`<div class="status-msg success">✅ ${this.successMessage}</div>` : ''}
      ${!this.previewUrl ? html`
        <runefoble-map-dropzone
          .uploadEndpoint="${this.uploadEndpoint}" .ownerId="${this.ownerId}"
          .assetType="${this.assetType}" .isUploading="${this.isUploading}"
          .uploadProgress="${this.uploadProgress}"
          @upload-start="${() => { this.isUploading = true; this.uploadProgress = 15; this.errorMessage = null; }}"
          @upload-progress="${(e: CustomEvent<{ progress: number }>) => { this.uploadProgress = e.detail.progress; }}"
          @upload-success="${this.handleUploadSuccess}"
          @upload-error="${(e: CustomEvent<{ message: string }>) => { this.errorMessage = e.detail.message; this.isUploading = false; }}"
        ></runefoble-map-dropzone>
      ` : html`
        <runefoble-map-grid-config
          class="shroud-overlay"
          .previewUrl="${this.previewUrl}" .gridCols="${this.gridCols}"
          .gridRows="${this.gridRows}" .gridOpacity="${this.gridOpacity}"
          .shroudOpacity="${this.shroudOpacity}" .shroudEnabled="${this.shroudEnabled}"
          .revealedCells="${this.revealedCells}" @grid-change="${this.handleGridChange}"
        ></runefoble-map-grid-config>
      `}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-map-uploader': RunefobleMapUploader;
  }
}
