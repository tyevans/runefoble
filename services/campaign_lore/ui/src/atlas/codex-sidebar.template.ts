import { html, type TemplateResult } from 'lit';
import type { CodexEntry } from './types.ts';

export interface CodexSidebarProps {
  codexEntries: CodexEntry[];
  activeLayer: string;
  activeEra: string;
  selectedEntryId?: string;
  onSelectLayer: (layer: string) => void;
  onEraInput: (era: string) => void;
  onSelectEntry: (entry: CodexEntry) => void;
}

export function renderCodexSidebar(props: CodexSidebarProps): TemplateResult {
  const { codexEntries, activeLayer, activeEra, selectedEntryId, onSelectLayer, onEraInput, onSelectEntry } = props;
  const layers = ['continental', 'regional', 'municipal'];

  return html`
    <div class="drawer">
      <div class="drawer-header">
        <span>Layers & Codex</span>
        <span style="font-size: 0.75rem; color: #666;">${codexEntries.length} notes</span>
      </div>

      <div class="drawer-content">
        <div class="filter-group">
          <span class="filter-label">Zoom Layer</span>
          <div class="layer-selector">
            ${layers.map(
              (layer) => html`
                <button
                  class="layer-btn ${activeLayer === layer ? 'selected' : ''}"
                  @click=${() => onSelectLayer(layer)}
                >
                  ${layer.charAt(0).toUpperCase() + layer.slice(1)}
                </button>
              `
            )}
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label">Chronological Era</span>
          <input
            type="text"
            class="era-input"
            placeholder="Filter era / session..."
            .value=${activeEra}
            @input=${(e: Event) => onEraInput((e.target as HTMLInputElement).value)}
          />
        </div>

        <div class="filter-group">
          <span class="filter-label">Collaborative Codex</span>
          ${codexEntries.map((entry) => {
            const isSelected = selectedEntryId === entry.entry_id;
            const text = entry.content.length > 80 ? entry.content.slice(0, 80) + '...' : entry.content;
            return html`
              <div
                class="codex-card ${isSelected ? 'selected' : ''}"
                data-entry-id=${entry.entry_id}
                @click=${() => onSelectEntry(entry)}
              >
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <strong style="font-size: 0.85rem;">${entry.title}</strong>
                  <span class="privacy-tag ${entry.privacy}">${entry.privacy.replace('_', ' ')}</span>
                </div>
                <div class="entry-body">${text}</div>
                ${entry.linked_entities && entry.linked_entities.length > 0
                  ? html`
                      <div style="margin-top: 4px;">
                        ${entry.linked_entities.map(
                          (ent) => html`<span class="entity-tag">${ent.name}</span>`
                        )}
                      </div>
                    `
                  : ''}
              </div>
            `;
          })}
        </div>
      </div>
    </div>
  `;
}
