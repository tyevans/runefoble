import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { mapUploaderStyles } from './runefoble-map-uploader.styles.ts';

export interface DropzoneUploadSuccessDetail {
  assetId: string;
  downloadUrl: string;
  filename: string;
  byteSize: number;
  contentType: string;
  resolution: { width: number; height: number };
}

@customElement('runefoble-map-dropzone')
export class RunefobleMapDropzone extends LitElement {
  static styles = mapUploaderStyles;

  @property({ type: String }) uploadEndpoint = '/api/v1/assets/upload';
  @property({ type: String }) ownerId = 'gm-host';
  @property({ type: String }) assetType = 'battlemap';
  @property({ type: Boolean }) isUploading = false;
  @property({ type: Number }) uploadProgress = 0;
  @state() private isDragging = false;

  private emit<T>(name: string, detail: T) {
    this.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true, detail }));
  }

  private handleDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging = false;
    if (e.dataTransfer?.files.length) this.uploadFile(e.dataTransfer.files[0]);
  }

  private handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files?.length) this.uploadFile(input.files[0]);
  }

  private async uploadFile(file: File) {
    if (!file.type.startsWith('image/')) {
      this.emit('upload-error', { message: 'Selected file must be an image (PNG, JPEG, WebP, SVG).' });
      return;
    }
    const localUrl = URL.createObjectURL(file);
    const img = new Image();
    img.src = localUrl;
    this.isUploading = true;
    this.uploadProgress = 15;
    this.emit('upload-start', { file, previewUrl: localUrl });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('owner_id', this.ownerId);
    formData.append('asset_type', this.assetType);

    try {
      this.uploadProgress = 50;
      this.emit('upload-progress', { progress: 50 });
      const response = await fetch(this.uploadEndpoint, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`Upload failed with status ${response.status}`);

      this.uploadProgress = 100;
      const data = await response.json();
      const resolution = { width: img.naturalWidth || 1920, height: img.naturalHeight || 1080 };
      this.emit<DropzoneUploadSuccessDetail>('upload-success', {
        assetId: data.asset_id,
        downloadUrl: data.download_url || localUrl,
        filename: file.name,
        byteSize: data.byte_size || file.size,
        contentType: data.content_type || file.type,
        resolution,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload battlemap.';
      this.emit('upload-error', { message });
    } finally {
      this.isUploading = false;
    }
  }

  render() {
    if (this.isUploading) {
      return html`
        <div class="progress-section">
          <div class="progress-header">
            <span>Uploading battlemap to Silo S3...</span>
            <span>${this.uploadProgress}%</span>
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${this.uploadProgress}%"></div>
          </div>
        </div>
      `;
    }
    return html`
      <div
        class="dropzone ${this.isDragging ? 'dragging' : ''}"
        @dragover="${(e: DragEvent) => { e.preventDefault(); this.isDragging = true; }}"
        @dragleave="${(e: DragEvent) => { e.preventDefault(); this.isDragging = false; }}"
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
        <button type="button" class="btn btn-primary" style="margin-top: 8px;">Browse Files</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-map-dropzone': RunefobleMapDropzone;
  }
}
