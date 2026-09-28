import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { RadialActionItem, RadialActionType } from './board-types.ts';
import { radialMenuStyles } from './radial/radial_menu.styles.ts';
import { RADIAL_ACTIONS, calculateWedgePosition, renderWedge } from './radial/radial_wedge.ts';

export * from './radial/index.ts';

@customElement('runefoble-radial-menu')
export class RunefobleRadialMenu extends LitElement {
  static styles = radialMenuStyles;

  @property({ type: String }) tokenId = '';
  @property({ type: String }) tokenName = '';
  @property({ type: Number }) radius = 68;
  @property({ type: Array }) actions: RadialActionItem[] = RADIAL_ACTIONS;

  @state() private hoveredAction: RadialActionItem | null = null;

  private handleActionClick(e: Event, action: RadialActionType) {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('action-select', {
      detail: { action, tokenId: this.tokenId, tokenName: this.tokenName },
      bubbles: true, composed: true,
    }));
  }

  private handleClose(e: Event) {
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent('menu-close', {
      detail: { tokenId: this.tokenId },
      bubbles: true, composed: true,
    }));
  }

  private handlePointerDownWedge(e: PointerEvent, action: RadialActionItem) {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    this.hoveredAction = action;
  }

  private handlePointerUpWedge(e: PointerEvent, action: RadialActionType) {
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}
    this.handleActionClick(e, action);
  }

  render() {
    const count = this.actions.length;

    return html`
      <div class="backdrop" @click="${(e: Event) => this.handleClose(e)}"></div>
      <div class="radial-container">
        <button
          class="center-button"
          @click="${(e: Event) => this.handleClose(e)}"
          title="Dismiss action menu"
          aria-label="Close action dial"
        >✕</button>

        ${this.actions.map((act, index) => {
          const { x, y } = calculateWedgePosition(index, count, this.radius);
          return renderWedge({
            action: act,
            isActive: this.hoveredAction?.id === act.id,
            x, y,
            onMouseEnter: () => { this.hoveredAction = act; },
            onMouseLeave: () => { this.hoveredAction = null; },
            onPointerDown: (e: PointerEvent) => this.handlePointerDownWedge(e, act),
            onPointerUp: (e: PointerEvent) => this.handlePointerUpWedge(e, act.id),
            onClick: (e: Event) => this.handleActionClick(e, act.id),
          });
        })}

        ${this.hoveredAction ? html`
          <div class="tooltip">
            <strong>${this.hoveredAction.label}</strong>: ${this.hoveredAction.description}
          </div>
        ` : null}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-radial-menu': RunefobleRadialMenu;
  }
}
