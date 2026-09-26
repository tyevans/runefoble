import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface MonsterEntity {
  id: string;
  name: string;
  cr: string;
  hp: number;
  max_hp: number;
  ac: number;
  role: string;
  position?: { x: number; y: number };
}

export interface AutonomousActionDetail {
  actor_name: string;
  action_type: string;
  target_name: string;
  narrative: string;
  hp_impact: number;
}

@customElement('runefoble-autonomous-dm')
export class RunefobleAutonomousDm extends LitElement {
  @property({ type: String }) sessionId = '';
  @property({ type: String }) locationName = 'Forgotten Underhalls';
  @property({ type: String }) lighting = 'dim flickering torches casting elongated shadows';
  @property({ type: String }) mood = 'suspenseful';
  @property({ type: String }) description = 'Damp stonework glistens under dying torchlight. The distant drip of water echoes like a ticking clock.';
  @property({ type: String }) ambientAudioPrompt = 'subterranean dungeon ambiance, distant water dripping, damp cavern';

  @property({ type: String }) encounterName = 'Cavern Skirmish Squad';
  @property({ type: String }) threatLevel = 'medium';
  @property({ type: String }) tacticalObjective = 'Eliminate the frontline warriors and isolate the goblin shaman.';
  @property({ type: Array }) monsters: MonsterEntity[] = [
    { id: 'mon-1', name: 'Goblin Boss', cr: '1', hp: 21, max_hp: 21, ac: 17, role: 'boss' },
    { id: 'mon-2', name: 'Goblin Shaman', cr: '1', hp: 18, max_hp: 18, ac: 12, role: 'caster' },
    { id: 'mon-3', name: 'Goblin Cutthroat', cr: '1/4', hp: 9, max_hp: 9, ac: 14, role: 'skirmisher' },
  ];

  @property({ type: Object }) lastAction: AutonomousActionDetail | null = null;

  @state() private selectedLocation = 'dungeon';
  @state() private selectedMood = 'suspenseful';
  @state() private selectedDifficulty = 'medium';

  static styles = css`
    :host {
      display: block;
      font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
      color: var(--rf-text-primary);
      background: var(--rf-bg-surface);
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow);
      padding: 20px;
      box-sizing: border-box;
      max-width: 640px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
      padding-bottom: 12px;
      margin-bottom: 16px;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .title-group h3 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 900;
      letter-spacing: -0.02em;
      text-transform: uppercase;
    }

    .badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 3px 8px;
      border: 1px solid var(--rf-border-color);
      letter-spacing: 0.05em;
    }

    .badge-lighting {
      background: var(--rf-accent-tertiary);
      color: var(--rf-text-primary);
    }

    .badge-threat {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }

    .badge-threat.easy {
      background: var(--rf-success, var(--rf-accent-secondary));
      color: var(--rf-text-inverse);
    }

    .badge-threat.medium {
      background: var(--rf-warning, var(--rf-accent-tertiary));
      color: var(--rf-text-primary);
    }

    .badge-threat.hard {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }

    .badge-threat.deadly {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }

    .scene-box {
      background: var(--rf-bg-canvas);
      border: 1px solid var(--rf-border-color);
      padding: 12px;
      margin-bottom: 14px;
    }

    .scene-title {
      font-weight: 800;
      font-size: 1rem;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .scene-desc {
      font-size: 0.88rem;
      line-height: 1.45;
      margin: 6px 0;
      color: var(--rf-text-primary);
    }

    .ambient-audio {
      font-size: 0.78rem;
      color: var(--rf-text-muted);
      font-style: italic;
      margin-top: 4px;
    }

    .encounter-section {
      margin-top: 14px;
    }

    .section-title {
      font-size: 0.85rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .tactical-obj {
      font-size: 0.82rem;
      padding: 6px 10px;
      background: var(--rf-bg-inset, var(--rf-bg-canvas));
      border: 1px solid var(--rf-border-subtle, var(--rf-border-color));
      color: var(--rf-text-secondary, var(--rf-text-primary));
      font-weight: 600;
      margin-bottom: 10px;
    }

    .monsters-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }

    .monster-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 10px;
      border: 1px solid var(--rf-border-subtle, var(--rf-border-color));
      background: var(--rf-bg-surface);
      font-size: 0.82rem;
    }

    .monster-name {
      font-weight: 700;
    }

    .monster-stats {
      font-family: monospace;
      font-size: 0.78rem;
      color: var(--rf-text-muted);
    }

    .action-resolved-box {
      margin-top: 12px;
      padding: 10px;
      border: 2px solid var(--rf-accent-primary);
      background: var(--rf-bg-inset, var(--rf-bg-canvas));
      color: var(--rf-accent-primary);
      font-size: 0.82rem;
    }

    .action-resolved-title {
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 4px;
    }

    .controls-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 8px;
      margin-top: 16px;
      padding-top: 14px;
      border-top: var(--rf-border-width, 2px) solid var(--rf-border-color);
    }

    button.rf-btn {
      font-family: inherit;
      font-size: 0.82rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 10px 8px;
      cursor: pointer;
      border: var(--rf-border-width, 2px) solid var(--rf-border-color);
      border-radius: var(--rf-border-radius, 0px);
      box-shadow: var(--rf-shadow-sm);
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }

    button.rf-btn:hover {
      transform: translate(-1px, -1px);
      box-shadow: var(--rf-shadow);
    }

    button.rf-btn:active {
      transform: translate(1px, 1px);
      box-shadow: none;
    }

    .btn-scene {
      background: var(--rf-accent-secondary);
      color: var(--rf-text-inverse);
    }

    .btn-encounter {
      background: var(--rf-accent-tertiary);
      color: var(--rf-text-primary);
    }

    .btn-turn {
      background: var(--rf-accent-primary);
      color: var(--rf-text-inverse);
    }
  `;

  private handleGenerateScene() {
    this.dispatchEvent(
      new CustomEvent('generate-scene', {
        detail: {
          locationType: this.selectedLocation,
          mood: this.selectedMood,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleSpawnEncounter() {
    this.dispatchEvent(
      new CustomEvent('spawn-encounter', {
        detail: {
          partyLevel: 3,
          partySize: 4,
          difficulty: this.selectedDifficulty,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleExecuteNpcTurn() {
    const actor = this.monsters.length > 0 ? this.monsters[0].name : 'Goblin Boss';
    this.dispatchEvent(
      new CustomEvent('execute-npc-turn', {
        detail: {
          actorName: actor,
          roundNumber: 1,
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    return html`
      <div class="header">
        <div class="title-group">
          <h3>The Watcher DM Engine</h3>
          <span class="badge badge-lighting">${this.mood}</span>
        </div>
        <span class="badge badge-threat ${this.threatLevel}">${this.threatLevel} Threat</span>
      </div>

      <div class="scene-box">
        <div class="scene-title">
          <span>📍 ${this.locationName}</span>
          <span class="badge badge-lighting" style="font-size: 0.65rem;">${this.lighting}</span>
        </div>
        <div class="scene-desc">${this.description}</div>
        <div class="ambient-audio">🎵 Ambient: "${this.ambientAudioPrompt}"</div>
      </div>

      <div class="encounter-section">
        <div class="section-title">
          <span>⚔️ Encounter: ${this.encounterName}</span>
          <span style="font-size: 0.75rem; color: var(--rf-text-muted);">${this.monsters.length} Active Tokens</span>
        </div>

        ${this.tacticalObjective
          ? html`<div class="tactical-obj">🎯 Objective: ${this.tacticalObjective}</div>`
          : ''}

        <div class="monsters-list">
          ${this.monsters.map(
            (mon) => html`
              <div class="monster-item">
                <span class="monster-name">${mon.name} <small>(${mon.role})</small></span>
                <span class="monster-stats">CR ${mon.cr} | HP ${mon.hp}/${mon.max_hp} | AC ${mon.ac}</span>
              </div>
            `
          )}
        </div>
      </div>

      ${this.lastAction
        ? html`
            <div class="action-resolved-box">
              <div class="action-resolved-title">
                ⚡ Action: ${this.lastAction.actor_name} &rarr; ${this.lastAction.target_name} (${this.lastAction.action_type})
              </div>
              <div>${this.lastAction.narrative}</div>
              <div style="font-weight: 700; margin-top: 4px;">Impact: ${this.lastAction.hp_impact} HP</div>
            </div>
          `
        : ''}

      <div class="controls-grid">
        <button class="rf-btn btn-scene" @click=${this.handleGenerateScene}>
          Generate Scene
        </button>
        <button class="rf-btn btn-encounter" @click=${this.handleSpawnEncounter}>
          Spawn Encounter
        </button>
        <button class="rf-btn btn-turn" @click=${this.handleExecuteNpcTurn}>
          Execute NPC Turn
        </button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-autonomous-dm': RunefobleAutonomousDm;
  }
}
