import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * Explicit error state for a failed App Shell read (TASK-0640).
 * Shows "not found" for HTTP 404. Shows a retry control for every other failure.
 * It never shows canned data in place of the failed read.
 */
@customElement('runefoble-data-error')
export class RunefobleDataError extends LitElement {
  @property({ type: Number }) status = 0;
  @property({ type: String }) message = '';

  static styles = css`
    :host { display: block; padding: 2rem; font-family: var(--rf-font-body, sans-serif); color: var(--rf-text-primary, inherit); }
    h2 { margin: 0 0 0.5rem; font-size: 1.4rem; }
    p { margin: 0 0 1rem; }
    button { padding: 0.5rem 1rem; border: 2px solid currentColor; background: transparent; color: inherit; cursor: pointer; }
  `;

  render() {
    const notFound = this.status === 404;
    return html`
      <section role="alert" aria-live="assertive">
        <h2>${notFound ? 'Not found' : 'Could not load this view'}</h2>
        <p>${notFound ? 'This item does not exist or you cannot see it.' : this.message}</p>
        ${notFound ? '' : html`<button type="button" @click=${this.retry}>Retry</button>`}
      </section>
    `;
  }

  private retry = () => {
    this.dispatchEvent(new CustomEvent('retry', { bubbles: true, composed: true }));
  };
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-data-error': RunefobleDataError;
  }
}
