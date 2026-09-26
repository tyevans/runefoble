import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { spectatorOverlayStyles } from './runefoble-spectator-overlay.styles.ts';

export interface OverlayPartyMember {
  id: string;
  name: string;
  hp: number;
  maxHp: number;
  tempHp?: number;
  conditions?: string[];
  isAiControlled?: boolean;
  color?: string;
  isActiveTurn?: boolean;
}

export interface OverlayCameraTarget {
  targetX: number;
  targetY: number;
  zoom: number;
  durationMs: number;
  easing: string;
  activeTokenId?: string;
  reason?: string;
}

export interface OverlayRollAnimation {
  rollerName: string;
  diceFormula: string;
  result: number;
  isCritical?: boolean;
  isFumble?: boolean;
}

@customElement('runefoble-spectator-overlay')
export class RunefobleSpectatorOverlay extends LitElement {
  static styles = [spectatorOverlayStyles];

  @property({ type: String, attribute: 'session-id' }) sessionId = 'session-1';
  @property({ type: String }) position: 'bottom' | 'top' | 'sidebar' = 'bottom';
  @property({ type: Boolean, attribute: 'transparent-mode', reflect: true }) transparentMode = true;
  @property({ type: Array }) party: OverlayPartyMember[] = [];
  @property({ type: Object }) camera: OverlayCameraTarget = {
    targetX: 0,
    targetY: 0,
    zoom: 1.5,
    durationMs: 300,
    easing: 'cubic-bezier(0.25, 0.1, 0.25, 1.0)',
  };
  @property({ type: Object }) activeRoll: OverlayRollAnimation | null = null;
  @property({ type: Number }) round = 1;
  @property({ type: Boolean, attribute: 'connect-ws' }) connectWs = false;

  @state() private ws: WebSocket | null = null;

  connectedCallback() {
    super.connectedCallback();
    if (this.connectWs && typeof WebSocket !== 'undefined') {
      this.initWebSocket();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private initWebSocket() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/overlay/${this.sessionId}`;
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.party) this.party = msg.party;
          if (msg.camera) {
            this.camera = {
              targetX: msg.camera.target_x ?? msg.camera.targetX ?? 0,
              targetY: msg.camera.target_y ?? msg.camera.targetY ?? 0,
              zoom: msg.camera.zoom ?? 1.5,
              durationMs: msg.camera.duration_ms ?? msg.camera.durationMs ?? 300,
              easing: msg.camera.easing ?? 'cubic-bezier(0.25, 0.1, 0.25, 1.0)',
            };
          }
          if (msg.type === 'roll_animation') {
            this.triggerRollAnimation({
              rollerName: msg.roller_name,
              diceFormula: msg.dice_formula,
              result: msg.result,
              isCritical: msg.is_critical,
              isFumble: msg.is_fumble,
            });
          }
        } catch {
          // ignore malformed payloads
        }
      };
    } catch {
      // ignore offline fallback
    }
  }

  triggerRollAnimation(roll: OverlayRollAnimation, durationMs = 3500) {
    this.activeRoll = roll;
    setTimeout(() => {
      if (this.activeRoll === roll) {
        this.activeRoll = null;
      }
    }, durationMs);
  }

  private getHealthStatusClass(hp: number, maxHp: number): string {
    if (maxHp <= 0) return 'healthy';
    const ratio = hp / maxHp;
    if (ratio <= 0.25) return 'critical';
    if (ratio <= 0.5) return 'wounded';
    return 'healthy';
  }

  render() {
    return html`
      <!-- Camera Director Target Indicator -->
      <div class="camera-hud-badge" title="Cinematic Director Camera Active">
        <span class="camera-indicator-dot"></span>
        <span>DIR: (${this.camera.targetX.toFixed(1)}, ${this.camera.targetY.toFixed(1)}) @ ${this.camera.zoom}x</span>
      </div>

      <!-- Animated Dice Roll Banner -->
      ${this.activeRoll
        ? html`
            <div class="roll-banner-container">
              <div
                class="roll-banner ${this.activeRoll.isCritical ? 'crit' : ''} ${this.activeRoll.isFumble ? 'fumble' : ''}"
              >
                <div>
                  <div class="roll-roller">${this.activeRoll.rollerName}</div>
                  <div class="roll-formula">${this.activeRoll.diceFormula}</div>
                </div>
                <div class="roll-result">${this.activeRoll.result}</div>
                ${this.activeRoll.isCritical ? html`<span class="ai-tag">CRITICAL!</span>` : ''}
                ${this.activeRoll.isFumble ? html`<span class="status-badge">FUMBLE!</span>` : ''}
              </div>
            </div>
          `
        : ''}

      <!-- Party Vitals HUD -->
      <div class="overlay-container ${this.position}">
        ${this.party.map((member) => {
          const ratio = member.maxHp > 0 ? Math.max(0, Math.min(100, (member.hp / member.maxHp) * 100)) : 0;
          const statusClass = this.getHealthStatusClass(member.hp, member.maxHp);
          const color = member.color || (member.isAiControlled ? '#f59e0b' : '#3b82f6');
          return html`
            <div class="party-vitals-card ${member.isActiveTurn ? 'active-turn' : ''}">
              <div class="card-top">
                <span class="character-name">
                  <span class="avatar-badge" style="background: ${color}">
                    ${member.name.slice(0, 2).toUpperCase()}
                  </span>
                  ${member.name}
                </span>
                <span class="hp-counter">
                  <strong>${member.hp}</strong> / ${member.maxHp} HP
                </span>
              </div>

              <!-- Animated HP Bar Track -->
              <div class="hp-bar-track">
                <div class="hp-bar-fill ${statusClass}" style="width: ${ratio}%;"></div>
              </div>

              <!-- Conditions and Status Tags -->
              <div class="badges-row">
                ${member.isActiveTurn ? html`<span class="turn-tag">ACTIVE TURN</span>` : ''}
                ${member.isAiControlled ? html`<span class="ai-tag">STAND-IN</span>` : ''}
                ${(member.conditions || []).map((cond) => html`<span class="status-badge">${cond}</span>`)}
              </div>
            </div>
          `;
        })}
        <slot></slot>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-spectator-overlay': RunefobleSpectatorOverlay;
  }
}
