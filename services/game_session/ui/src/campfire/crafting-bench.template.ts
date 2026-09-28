import { html, nothing } from 'lit';
import type { CraftingBenchProps } from './types.ts';

export function renderCraftingBench(props: CraftingBenchProps) {
  const riskPercentage = Math.round(props.calculatedRisk * 100);
  const riskClass = props.calculatedRisk < 0.35 ? 'low' : props.calculatedRisk < 0.6 ? 'med' : 'high';

  return html`
    <div class="panel" style="margin-top: 20px;">
      <div class="panel-header"><span>⚗️</span> Alchemical Crucible Workbench</div>

      <div style="font-weight: 700; font-size: 0.85rem; margin-bottom: 6px;">Available Reagents</div>
      <div class="reagents-tray">
        ${props.availableReagents.map(
          (r) => html`
            <span
              class="chip ${props.selectedReagents.includes(r) ? 'selected' : ''}"
              @click="${() => props.onToggleReagent(r)}"
            >
              ${props.selectedReagents.includes(r) ? '✓ ' : '+ '} ${r}
            </span>
          `
        )}
      </div>

      <div class="crucible-chamber">
        <div class="crucible-title">Crucible Mixing Chamber (Max 3 Reagents)</div>
        <div class="crucible-slots">
          ${props.selectedReagents.length === 0
            ? html`<span style="color: #64748b; font-style: italic;">Select reagents from tray above...</span>`
            : props.selectedReagents.map((r) => html`<span class="chip selected">${r}</span>`)}
        </div>
      </div>

      <div class="catalyst-selector">
        <label><strong>Catalyst:</strong></label>
        <select @change="${props.onCatalystChange}">
          <option value="none" ?selected="${props.selectedCatalyst === 'none'}">None (Raw Mix)</option>
          <option value="purified_water" ?selected="${props.selectedCatalyst === 'purified_water'}">Purified Spring Water (-20% Risk)</option>
          <option value="dragon_bile" ?selected="${props.selectedCatalyst === 'dragon_bile'}">Dragon Bile (+2 Potency, +15% Risk)</option>
          <option value="quicksilver" ?selected="${props.selectedCatalyst === 'quicksilver'}">Purified Quicksilver (Stabilizer)</option>
          <option value="spirit_ash" ?selected="${props.selectedCatalyst === 'spirit_ash'}">Spirit Ash (Blessed Radiant)</option>
        </select>
      </div>

      <div class="risk-meter">
        <div class="risk-header">
          <span>Volatile Mishap Probability:</span>
          <span>${riskPercentage}%</span>
        </div>
        <div class="risk-bar">
          <div class="risk-fill ${riskClass}" style="width: ${riskPercentage}%"></div>
        </div>
      </div>

      <button
        class="btn btn-primary"
        ?disabled="${props.selectedReagents.length === 0}"
        @click="${props.onCombine}"
      >
        Transmute & Combine Reagents
      </button>

      ${props.lastOutcome
        ? html`
            <div class="outcome-box ${props.lastOutcome.outcome}">
              <strong>${props.lastOutcome.outcome === 'success' ? 'Alchemy Success:' : 'Mishap Alert:'}</strong>
              <p style="margin: 4px 0 0 0;">${props.lastOutcome.message}</p>
              ${props.lastOutcome.tags
                ? html`
                    <div style="margin-top: 6px; display: flex; gap: 4px;">
                      ${props.lastOutcome.tags.map((t) => html`<span class="boon-tag">${t}</span>`)}
                    </div>
                  `
                : nothing}
            </div>
          `
        : nothing}
    </div>
  `;
}
