/**
 * Session recap (TASK-0953). Lists the chronicle lines of an ended session in commit order, with
 * the counts of dice rolls, token moves and stand-in actions. The element keeps no state of its
 * own. It shows the lines that the App Shell gives it, and it adds no text for a missing line.
 */

import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { recapCounts, type RecapEntry } from './recap-counts.ts';
import { sessionRecapStyles } from './runefoble-session-recap.styles.ts';

@customElement('runefoble-session-recap')
export class RunefobleSessionRecap extends LitElement {
  static styles = [sessionRecapStyles];

  @property({ type: String, attribute: 'session-title' }) sessionTitle = '';
  @property({ type: Array }) entries: RecapEntry[] = [];

  render() {
    const counts = recapCounts(this.entries);
    return html`<section class="session-recap" role="region" aria-label="Session recap">
      <h2>Session Recap${this.sessionTitle ? `: ${this.sessionTitle}` : ''}</h2>
      <ul class="recap-counts" aria-label="Recap counts">
        <li data-count="dice">Dice rolls: ${counts.diceRolls}</li>
        <li data-count="moves">Token moves: ${counts.tokenMoves}</li>
        <li data-count="stand-in">Stand-in actions: ${counts.standInActions}</li>
      </ul>
      <ol class="recap-lines" aria-label="Recap lines">
        ${this.entries.map((entry) => html`<li class="recap-line" data-kind="${entry.actionType ?? entry.source ?? ''}"><span class="speaker-name">${entry.speaker}</span><span class="recap-text">${entry.text}</span></li>`)}
      </ol>
    </section>`;
  }
}
