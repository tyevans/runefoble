import { LitElement, css, html, svg } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { RadialActionItem, RadialActionType } from './board-types.ts';

export const RADIAL_ACTIONS: RadialActionItem[] = [
  {
    id: 'attack',
    label: 'Attack',
    icon: 'attack',
    color: 'var(--rf-accent-primary, #e63946)',
    description: 'Execute melee or ranged weapon strike',
  },
  {
    id: 'dash',
    label: 'Dash',
    icon: 'dash',
    color: 'var(--rf-accent-tertiary, #ffb703)',
    description: 'Double movement budget for the turn',
  },
  {
    id: 'disengage',
    label: 'Disengage',
    icon: 'disengage',
    color: 'var(--rf-accent-secondary, #1d3557)',
    description: 'Movement does not provoke opportunity attacks',
  },
  {
    id: 'dodge',
    label: 'Dodge',
    icon: 'dodge',
    color: '#2a9d8f',
    description: 'Attacks against you have disadvantage until next turn',
  },
  {
    id: 'cast',
    label: 'Cast',
    icon: 'cast',
    color: '#9d4edd',
    description: 'Cast an AoE spell or tactical cantrip',
  },
];

function renderBauhausGlyph(icon: string) {
  switch (icon) {
    case 'attack':
      // Bauhaus sharp sword / blade triangle
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M19.7 4.3a1 1 0 0 0-1.4 0l-9.9 9.9-2.8-2.8a1 1 0 0 0-1.4 1.4l2.8 2.8-3.7 3.7a1 1 0 0 0 1.4 1.4l3.7-3.7 2.8 2.8a1 1 0 0 0 1.4-1.4l-2.8-2.8 9.9-9.9a1 1 0 0 0 0-1.4z" />
          <polygon points="19,3 21,5 15,11 13,9" />
        </svg>
      `;
    case 'dash':
      // Bauhaus lightning bolt / kinetic arrow
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <polygon points="13,2 4,14 11,14 9,22 20,10 13,10" />
        </svg>
      `;
    case 'disengage':
      // Bauhaus curved escape retreat arrow
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M9 6l-5 5 5 5V13h8a4 4 0 0 1 4 4v3h2v-3a6 6 0 0 0-6-6H9V6z" />
          <circle cx="18" cy="7" r="2.5" />
        </svg>
      `;
    case 'dodge':
      // Bauhaus geometric shield
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M12 2L4 5v6.5C4 16.8 7.4 21.6 12 23c4.6-1.4 8-6.2 8-11.5V5l-8-3zm0 2.2l6 2.3v5.2c0 4.1-2.6 8-6 9.3-3.4-1.3-6-5.2-6-9.3V6.5l6-2.3z" />
          <polygon points="12,6 16,9 12,18 8,9" />
        </svg>
      `;
    case 'cast':
      // Bauhaus geometric arcane star / rune
      return svg`
        <svg viewBox="0 0 24 24" class="glyph" fill="currentColor">
          <path d="M12 2l2.4 6.9L21.3 10l-5.3 4.6 1.7 7.1-5.7-3.6-5.7 3.6 1.7-7.1-5.3-4.6 6.9-1.1L12 2z" />
        </svg>
      `;
    default:
      return svg`<circle cx="12" cy="12" r="6" fill="currentColor" />`;
  }
}

@customElement('runefoble-radial-menu')
export class RunefobleRadialMenu extends LitElement {
  static styles = css`
    :host {
      position: absolute;
      top: 0;
      left: 0;
      z-index: 1000;
      pointer-events: auto;
      user-select: none;
      -webkit-user-select: none;
    }

    .radial-container {
      position: relative;
      width: 0;
      height: 0;
      animation: bloom 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes bloom {
      from {
        transform: scale(0.2) rotate(-20deg);
        opacity: 0;
      }
      to {
        transform: scale(1) rotate(0deg);
        opacity: 1;
      }
    }

    .backdrop {
      position: fixed;
      inset: 0;
      z-index: -1;
      background: rgba(0, 0, 0, 0.25);
      cursor: default;
    }

    .center-button {
      position: absolute;
      top: -20px;
      left: -20px;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--rf-bg-surface-elevated, #ffffff);
      color: var(--rf-text-primary, #121212);
      border: 2px solid var(--rf-border-color, #121212);
      box-shadow: 2px 2px 0px var(--rf-shadow-color, #121212);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      z-index: 2;
      transition: transform 0.1s ease, background 0.1s ease;
    }

    .center-button:hover,
    .center-button:active {
      transform: scale(1.08);
      background: var(--rf-accent-primary, #e63946);
      color: #ffffff;
    }

    .action-wedge {
      position: absolute;
      width: 46px;
      height: 46px;
      margin-top: -23px;
      margin-left: -23px;
      border-radius: 50%;
      border: 2px solid var(--rf-border-color, #121212);
      box-shadow: 3px 3px 0px var(--rf-shadow-color, #121212);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: #ffffff;
      transition: transform 0.12s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.12s ease;
      touch-action: none;
    }

    .action-wedge:hover,
    .action-wedge.active {
      transform: scale(1.18);
      box-shadow: 4px 4px 0px var(--rf-shadow-color, #121212);
    }

    .glyph {
      width: 22px;
      height: 22px;
      filter: drop-shadow(1px 1px 0px rgba(0, 0, 0, 0.4));
    }

    .action-label {
      position: absolute;
      bottom: -18px;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      background: var(--rf-bg-surface-elevated, #ffffff);
      color: var(--rf-text-primary, #121212);
      padding: 1px 4px;
      border: 1px solid var(--rf-border-color, #121212);
      border-radius: 2px;
      white-space: nowrap;
      pointer-events: none;
      box-shadow: 1px 1px 0px var(--rf-shadow-color, #121212);
    }

    .tooltip {
      position: absolute;
      top: 56px;
      left: -90px;
      width: 180px;
      background: var(--rf-bg-surface-elevated, #ffffff);
      color: var(--rf-text-primary, #121212);
      border: 2px solid var(--rf-border-color, #121212);
      box-shadow: 3px 3px 0px var(--rf-shadow-color, #121212);
      padding: 6px 10px;
      font-size: 11px;
      text-align: center;
      pointer-events: none;
      font-weight: 600;
    }
  `;

  @property({ type: String }) tokenId = '';
  @property({ type: String }) tokenName = '';
  @property({ type: Number }) radius = 68;
  @property({ type: Array }) actions: RadialActionItem[] = RADIAL_ACTIONS;

  @state() private hoveredAction: RadialActionItem | null = null;

  private handleActionClick(e: Event, action: RadialActionType) {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('action-select', {
        detail: { action, tokenId: this.tokenId, tokenName: this.tokenName },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleClose(e: Event) {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('menu-close', {
        detail: { tokenId: this.tokenId },
        bubbles: true,
        composed: true,
      })
    );
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
    // Distribute angles starting from top-right (-72 degrees) evenly
    const angleStep = (2 * Math.PI) / count;
    const startAngle = -Math.PI / 2; // -90 deg (Top)

    return html`
      <div class="backdrop" @click="${(e: Event) => this.handleClose(e)}"></div>
      <div class="radial-container">
        <button
          class="center-button"
          @click="${(e: Event) => this.handleClose(e)}"
          title="Dismiss action menu"
          aria-label="Close action dial"
        >
          ✕
        </button>

        ${this.actions.map((act, index) => {
          const angle = startAngle + index * angleStep;
          const x = Math.round(this.radius * Math.cos(angle));
          const y = Math.round(this.radius * Math.sin(angle));

          return html`
            <div
              class="action-wedge ${this.hoveredAction?.id === act.id ? 'active' : ''}"
              style="left: ${x}px; top: ${y}px; background: ${act.color};"
              @mouseenter="${() => (this.hoveredAction = act)}"
              @mouseleave="${() => (this.hoveredAction = null)}"
              @pointerdown="${(e: PointerEvent) => this.handlePointerDownWedge(e, act)}"
              @pointerup="${(e: PointerEvent) => this.handlePointerUpWedge(e, act.id)}"
              @click="${(e: Event) => this.handleActionClick(e, act.id)}"
              title="${act.label}: ${act.description}"
              role="button"
              tabindex="0"
            >
              ${renderBauhausGlyph(act.icon)}
              <span class="action-label">${act.label}</span>
            </div>
          `;
        })}

        ${this.hoveredAction
          ? html`
              <div class="tooltip">
                <strong>${this.hoveredAction.label}</strong>:
                ${this.hoveredAction.description}
              </div>
            `
          : null}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-radial-menu': RunefobleRadialMenu;
  }
}
