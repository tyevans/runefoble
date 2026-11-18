/**
 * Shows a protected asset in `<img src>` (TASK-0785 follow-up).
 *
 * A forged or uploaded asset is read at `/api/v1/assets/{id}`. That route needs the bearer,
 * and `<img src>` cannot send it. The controller fetches the path with the bearer and keeps
 * a blob URL for the element. Any other URL (for example a data URL or a static portrait)
 * passes through unchanged.
 *
 * Lifecycle: a blob URL is revoked when the source changes, when a newer load replaces it,
 * and when the host disconnects. A load that finishes after a newer request is discarded.
 * A refused read sets `failure`. It never shows a substitute image.
 */

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import {
  fetchAssetObjectUrl,
  revokeAssetObjectUrl,
  type AssetFetchLike,
} from './asset-object-url.ts';

/** True for an authorized asset path. Only these need the bearer. */
export function isAuthorizedAssetPath(src: string): boolean {
  return src.startsWith('/api/v1/assets/');
}

export class AssetImageController implements ReactiveController {
  private source = '';
  private displayUrl = '';
  private ownedBlobUrl = '';
  private failureMessage = '';
  private generation = 0;
  private connected = false;
  private readonly host: ReactiveControllerHost;
  private readonly authHeaders: () => Promise<Record<string, string>>;
  private readonly fetchImpl: AssetFetchLike | undefined;

  constructor(
    host: ReactiveControllerHost,
    authHeaders: () => Promise<Record<string, string>>,
    fetchImpl?: AssetFetchLike,
  ) {
    this.host = host;
    this.authHeaders = authHeaders;
    this.fetchImpl = fetchImpl;
    host.addController(this);
  }

  /** The URL to put in `<img src>`. Empty while an asset loads or after a failure. */
  get url(): string {
    return this.displayUrl;
  }

  /** The message of the last refused read, or an empty string. */
  get failure(): string {
    return this.failureMessage;
  }

  /** Sets the source to show. Calling it again with the same source does nothing. */
  setSource(src: string): void {
    if (src === this.source) return;
    this.source = src;
    if (this.connected) void this.load();
  }

  hostConnected(): void {
    this.connected = true;
    if (this.source) void this.load();
  }

  hostDisconnected(): void {
    this.connected = false;
    this.generation += 1;
    this.showUrl('');
  }

  private async load(): Promise<void> {
    const generation = ++this.generation;
    this.failureMessage = '';
    if (!isAuthorizedAssetPath(this.source)) {
      this.showUrl(this.source);
      return;
    }
    this.showUrl('');
    try {
      const blobUrl = await fetchAssetObjectUrl(this.source, this.authHeaders, this.fetchImpl);
      if (generation !== this.generation) {
        revokeAssetObjectUrl(blobUrl);
        return;
      }
      this.showUrl(blobUrl);
    } catch (err) {
      if (generation !== this.generation) return;
      this.failureMessage = err instanceof Error ? err.message : 'Asset read failed.';
      this.host.requestUpdate();
    }
  }

  /** Shows `url` and revokes the blob URL this controller owned before. */
  private showUrl(url: string): void {
    revokeAssetObjectUrl(this.ownedBlobUrl);
    this.ownedBlobUrl = url.startsWith('blob:') ? url : '';
    this.displayUrl = url;
    this.host.requestUpdate();
  }
}
