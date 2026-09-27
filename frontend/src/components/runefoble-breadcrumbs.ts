/**
 * Runefoble Dynamic Breadcrumb Navigation Component
 * ADR-0004: Lit Web Components and Storybook UI
 * ADR-0012: Design System Theming and Bauhaus Modernism
 * TASK-0206: Dynamic Breadcrumb Navigation Component
 */

import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { router, type BreadcrumbItem } from '../router/router.ts';

@customElement('runefoble-breadcrumbs')
export class RunefobleBreadcrumbs extends LitElement {
  @property({ type: Array }) items: BreadcrumbItem[] = [];
  @property({ type: String }) separator = '›';
  @property({ type: Boolean }) autoRouter = false;

  private unlistenRouter: (() => void) | null = null;

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, sans-serif);
    }
    .breadcrumbs {
      display: flex;
      align-items: center;
      font-size: var(--rf-font-size-sm, 0.85rem);
    }
    .breadcrumb-list {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      list-style: none;
      margin: 0;
      padding: 0;
      gap: 4px;
    }
    .breadcrumb-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .breadcrumb-link {
      display: inline-flex;
      align-items: center;
      color: var(--rf-text-muted, #64748b);
      text-decoration: none;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 2px 8px;
      background: transparent;
      border: var(--rf-border-width, 2px) solid transparent;
      transition: all var(--rf-transition-fast, 150ms);
      cursor: pointer;
    }
    .breadcrumb-link:hover {
      color: var(--rf-accent-primary, #e63946);
      background: var(--rf-bg-surface, #ffffff);
      border-color: var(--rf-border-color, #1a202c);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a202c);
      transform: translate(-1px, -1px);
    }
    .breadcrumb-link:active {
      transform: translate(1px, 1px);
      box-shadow: none;
    }
    .breadcrumb-link:focus-visible {
      outline: 2px solid var(--rf-accent-primary, #e63946);
      outline-offset: 2px;
    }
    .breadcrumb-current {
      display: inline-flex;
      align-items: center;
      color: var(--rf-text-primary, #1a202c);
      background: var(--rf-bg-surface, #ffffff);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a202c);
      box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a202c);
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 2px 8px;
    }
    .separator {
      color: var(--rf-text-muted, #94a3b8);
      font-weight: 800;
      font-size: 0.9rem;
      user-select: none;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.autoRouter) {
      const cur = router.getCurrentRoute();
      if (cur) this.items = cur.breadcrumbs;
      this.unlistenRouter = router.onRouteChanged((r) => {
        this.items = r.breadcrumbs;
      });
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.unlistenRouter) {
      this.unlistenRouter();
      this.unlistenRouter = null;
    }
  }

  private handleClick(e: MouseEvent, item: BreadcrumbItem) {
    e.preventDefault();
    this.dispatchEvent(new CustomEvent('breadcrumb-click', {
      detail: { item, path: item.path },
      bubbles: true,
      composed: true,
    }));
    if (item.path) {
      router.navigate(item.path);
    }
  }

  render() {
    if (!this.items || this.items.length === 0) return html``;

    return html`
      <nav class="breadcrumbs" aria-label="Breadcrumb">
        <ol class="breadcrumb-list">
          ${this.items.map((item, index) => {
            const isLast = index === this.items.length - 1;
            const isActive = item.active || isLast;
            return html`
              <li class="breadcrumb-item">
                ${isActive
                  ? html`<span class="breadcrumb-current" aria-current="page">${item.label}</span>`
                  : html`<a
                      href="${item.path || '#'}"
                      class="breadcrumb-link"
                      @click=${(e: MouseEvent) => this.handleClick(e, item)}
                    >${item.label}</a>`}
                ${!isLast ? html`<span class="separator" aria-hidden="true">${this.separator}</span>` : ''}
              </li>
            `;
          })}
        </ol>
      </nav>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-breadcrumbs': RunefobleBreadcrumbs;
  }
}
