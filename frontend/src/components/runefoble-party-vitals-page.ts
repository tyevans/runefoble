/**
 * OBS party vitals page (TASK-0823 review).
 *
 * The App Shell route `#/overlay/party-vitals/:sessionId` renders this element and nothing else.
 * It reads the owner state once from the gateway JSON route, then mounts the vendored
 * `<runefoble-spectator-overlay>`. The overlay keeps itself current over its WebSocket.
 * The page sets the document background to transparent while it is mounted, so OBS can
 * composite it over the scene.
 */

import { LitElement, css, html, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import '@runefoble/game-session-ui/runefoble-spectator-overlay';
import {
  DEFAULT_OVERLAY_DURATION_MS,
  DEFAULT_OVERLAY_EASING,
  fetchPartyVitals,
  toOverlayCamera,
  toOverlayParty,
  type OverlayFetcher,
  type OverlayPosition,
  type PartyVitalsReply,
} from '../app/party-vitals-overlay.ts';

export const OBS_TRANSPARENT_CLASS = 'obs-transparent';

@customElement('runefoble-party-vitals-page')
export class RunefoblePartyVitalsPage extends LitElement {
  static styles = css`
    :host { display: block; background: transparent; }
    .overlay-error { color: #fecaca; background: rgba(15, 23, 42, 0.9); padding: 8px 12px; margin: 16px; }
  `;

  @property({ type: String, attribute: 'session-id' }) sessionId = '';
  @property({ type: String }) position: OverlayPosition = 'bottom';
  @property({ type: String }) easing = DEFAULT_OVERLAY_EASING;
  @property({ type: Number }) duration = DEFAULT_OVERLAY_DURATION_MS;
  /** The read of the owner state. Tests replace it. The default calls the gateway. */
  @property({ attribute: false }) fetcher: OverlayFetcher = fetchPartyVitals;

  @state() private vitals: PartyVitalsReply | null = null;
  @state() private error = '';
  private loadedKey = '';

  connectedCallback() {
    super.connectedCallback();
    document.documentElement.classList.add(OBS_TRANSPARENT_CLASS);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    document.documentElement.classList.remove(OBS_TRANSPARENT_CLASS);
  }

  protected updated(changed: PropertyValues<this>) {
    if (changed.has('sessionId') || changed.has('position')) void this.load();
  }

  private async load() {
    const key = `${this.sessionId}|${this.position}`;
    if (!this.sessionId || key === this.loadedKey) return;
    this.loadedKey = key;
    const result = await this.fetcher(this.sessionId, this.position);
    if (key !== `${this.sessionId}|${this.position}`) return;
    if (result.ok) {
      this.vitals = result.data;
      this.error = '';
    } else {
      this.vitals = null;
      this.error = result.message;
    }
  }

  render() {
    if (this.error) return html`<p class="overlay-error" role="alert">${this.error}</p>`;
    if (!this.vitals) return nothing;
    const style = `--overlay-easing: ${this.easing}; --overlay-duration: ${this.duration}ms;`;
    return html`<runefoble-spectator-overlay
      session-id=${this.sessionId}
      position=${this.position}
      transparent-mode
      connect-ws
      style=${style}
      .party=${toOverlayParty(this.vitals.party)}
      .camera=${toOverlayCamera(this.vitals.camera)}
      .round=${this.vitals.round}
    ></runefoble-spectator-overlay>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-party-vitals-page': RunefoblePartyVitalsPage;
  }
}
