import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { autonomousDmStyles } from './runefoble-autonomous-dm.styles.ts';

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

  static styles = autonomousDmStyles;


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
