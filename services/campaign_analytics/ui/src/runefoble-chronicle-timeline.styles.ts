import { css } from 'lit';

export const chronicleTimelineStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, 'Space Grotesk', system-ui, sans-serif);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    padding: 16px;
    box-sizing: border-box;
  }

  .timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    padding-bottom: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .timeline-title {
    font-size: 1.1rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .scrubber-panel {
    background: var(--rf-bg-card, #f9f9f9);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 12px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    margin-bottom: 14px;
  }

  .scrubber-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .scrub-btn {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    color: var(--rf-text-primary, #121212);
    padding: 4px 8px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-family: inherit;
  }

  .scrub-btn:hover {
    background: var(--rf-bg-card, #f0f0f0);
    transform: translate(-1px, -1px);
  }

  .scrubber-slider {
    flex: 1;
    min-width: 140px;
    accent-color: var(--rf-accent-primary, #e63946);
    cursor: pointer;
  }

  .scrubber-info {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--rf-text-secondary, #4a4a4a);
  }

  .milestones-container {
    max-height: 380px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-right: 4px;
  }

  .milestone-card {
    background: var(--rf-bg-surface, #ffffff);
    border: 1px solid var(--rf-border-color, #121212);
    padding: 12px;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    cursor: pointer;
    transition: transform 0.15s ease, border-color 0.15s ease;
    position: relative;
  }

  .milestone-card:hover {
    transform: translate(-2px, -2px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .milestone-card.selected {
    border: 2px solid var(--rf-accent-primary, #e63946);
    background: var(--rf-bg-inset, #fffdfa);
  }

  .milestone-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }

  .badge-category {
    padding: 2px 8px;
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    border: 1px solid var(--rf-border-color, #121212);
  }

  .badge-category.session_start {
    background: #2a9d8f;
    color: #ffffff;
  }

  .badge-category.boss_encounter {
    background: #e63946;
    color: #ffffff;
  }

  .badge-category.character_knockout {
    background: #121212;
    color: #ffffff;
  }

  .badge-category.recap {
    background: #e9c46a;
    color: #121212;
  }

  .badge-category.session_end {
    background: #264653;
    color: #ffffff;
  }

  .badge-timestamp {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--rf-text-muted, #757575);
  }

  .milestone-title {
    font-size: 0.95rem;
    font-weight: 800;
    margin-bottom: 4px;
  }

  .milestone-desc {
    font-size: 0.8rem;
    line-height: 1.35;
    color: var(--rf-text-secondary, #333333);
    margin-bottom: 8px;
  }

  .audio-action-row {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    border-top: 1px dashed var(--rf-border-color, #e0e0e0);
    padding-top: 6px;
  }

  .audio-btn {
    background: var(--rf-accent-secondary, #2a9d8f);
    color: #ffffff;
    border: 1px solid var(--rf-border-color, #121212);
    padding: 4px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-family: inherit;
  }

  .audio-btn.playing {
    background: var(--rf-accent-primary, #e63946);
  }

  .audio-waves {
    display: inline-flex;
    gap: 2px;
    align-items: flex-end;
    height: 12px;
  }

  .audio-bar {
    width: 2px;
    background: #ffffff;
    height: 100%;
    animation: bounce 0.6s infinite ease-in-out alternate;
  }

  .audio-bar:nth-child(2) {
    animation-delay: 0.2s;
  }
  .audio-bar:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes bounce {
    from {
      height: 3px;
    }
    to {
      height: 12px;
    }
  }
`;
