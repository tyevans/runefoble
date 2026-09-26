import { html, nothing } from 'lit';
import type { DragKinematicsState, GhostPreviewState } from './board-types.ts';
import { calculateVectorLineCoordinates } from './ghost_preview.ts';

export function getHealthBarColor(hp: number, maxHp: number): string {
  const ratio = Math.max(0, Math.min(1, hp / maxHp));
  if (ratio > 0.5) return 'var(--rf-accent-secondary)';
  if (ratio > 0.2) return 'var(--rf-accent-tertiary)';
  return 'var(--rf-accent-primary)';
}

export function renderVectorOverlay(
  ghostVector: ReturnType<typeof calculateVectorLineCoordinates> | null
) {
  if (!ghostVector) return nothing;
  return html`
    <svg class="vector-overlay" style="width: 100%; height: 100%;">
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="5"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--rf-accent-primary)" />
        </marker>
      </defs>
      <line
        class="vector-line"
        x1="${ghostVector.x1}"
        y1="${ghostVector.y1}"
        x2="${ghostVector.x2}"
        y2="${ghostVector.y2}"
        marker-end="url(#arrow)"
      />
    </svg>
  `;
}

export function renderDistanceRuler(dragState: DragKinematicsState | null) {
  if (!dragState?.isDragging || dragState.totalDistanceFt <= 0) return nothing;
  return html`
    <div class="distance-ruler">
      <span>📍 Distance: ${dragState.totalDistanceFt} ft</span>
      ${dragState.difficultCells.length > 0
        ? html`<span>(▲ +${dragState.difficultCells.length * 5}ft terrain)</span>`
        : nothing}
      ${dragState.hazardCells.length > 0
        ? html`<span>(⚠️ Hazard Alert)</span>`
        : nothing}
    </div>
  `;
}

export function renderGhostBanner(
  ghost: GhostPreviewState | null,
  onConfirm: () => void,
  onCancel: () => void
) {
  if (!ghost) return nothing;
  return html`
    <div class="ghost-banner">
      <div class="ghost-info">
        <span>👻 Spoken Preview:</span>
        <span>${ghost.tokenName || 'Character'} moves to (${ghost.toX}, ${ghost.toY})</span>
        <span>• ${ghost.totalDistanceFt} ft</span>
        ${ghost.hazardTriggered
          ? html`<span style="color: var(--rf-accent-primary)">⚠️ Triggers ${ghost.hazardTriggered} (${ghost.damageDice})</span>`
          : nothing}
        <span class="ghost-timer">⏱️ ${ghost.remainingSeconds}s</span>
      </div>
      <div class="ghost-actions">
        <button
          class="btn btn-confirm"
          @click="${onConfirm}"
          title="Confirm movement to destination"
        >
          ✓ Confirm Move
        </button>
        <button
          class="btn btn-cancel"
          @click="${onCancel}"
          title="Cancel preview"
        >
          ✕ Cancel
        </button>
      </div>
    </div>
  `;
}
