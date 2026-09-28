import { html } from 'lit';
import type { BoonsDisplayProps } from './types.ts';

export function renderBoonsDisplay(props: BoonsDisplayProps) {
  return html`
    <div class="panel campfire-box">
      <div class="panel-header"><span>🔥</span> Campfire Rest Interlude</div>
      <div class="prompt-quote">"${props.storytellingPrompt}"</div>

      <div class="rest-controls">
        <div class="rest-toggle">
          <button
            class="${props.restType === 'short' ? 'active' : ''}"
            @click="${() => props.onSelectRestType('short')}"
          >
            Short Rest
          </button>
          <button
            class="${props.restType === 'long' ? 'active' : ''}"
            @click="${() => props.onSelectRestType('long')}"
          >
            Long Rest
          </button>
        </div>
        <button class="btn btn-flame" @click="${props.onRest}">
          Rest by Campfire
        </button>
      </div>

      <div style="margin-top: 16px;">
        <div style="font-weight: 700; font-size: 0.85rem; text-transform: uppercase;">
          Active Party Rest Boons
        </div>
        <div class="boons-tag-list">
          ${props.activeBoons.map((boon) => html`<span class="boon-tag">✦ ${boon}</span>`)}
        </div>
      </div>
    </div>
  `;
}
