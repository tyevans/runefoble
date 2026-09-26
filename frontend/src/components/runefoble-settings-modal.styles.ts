import { css } from 'lit';

export const settingsModalStyles = css`
  :host {
    display: contents;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #121212);
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    padding: 16px;
    box-sizing: border-box;
    animation: rf-fade-in 0.15s ease-out;
  }

  @keyframes rf-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal-dialog {
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    box-shadow: var(--rf-shadow, 6px 6px 0px #121212);
    width: 100%;
    max-width: 640px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: rf-slide-up 0.18s ease-out;
  }

  @keyframes rf-slide-up {
    from { transform: translateY(12px); opacity: 0.8; }
    to { transform: translateY(0); opacity: 1; }
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    background: var(--rf-bg-canvas, #f8f9fa);
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
  }

  .modal-title-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .modal-icon-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    background: var(--rf-color-yellow, #ffb703);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    font-size: 0.95rem;
  }

  .modal-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 900;
    letter-spacing: -0.02em;
  }

  .close-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    font-size: 1rem;
    font-weight: 800;
    cursor: pointer;
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }

  .close-btn:hover {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .close-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 0px 0px 0px #121212;
  }

  .nav-tabs {
    display: flex;
    gap: 4px;
    padding: 8px 16px 0;
    background: var(--rf-bg-canvas, #f8f9fa);
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    overflow-x: auto;
  }

  .tab-btn {
    padding: 8px 14px;
    font-size: 0.85rem;
    font-weight: 700;
    border: var(--rf-border-width, 2px) solid transparent;
    border-bottom: none;
    background: transparent;
    color: var(--rf-text-muted, #4b5563);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }

  .tab-btn:hover:not(.active) {
    color: var(--rf-text-primary, #121212);
    background: rgba(0, 0, 0, 0.05);
  }

  .tab-btn.active {
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border-color: var(--rf-border-color, #121212);
    border-bottom: 2px solid var(--rf-bg-surface, #ffffff);
    margin-bottom: -2px;
  }

  .modal-body {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .section-title {
    font-size: 0.82rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0 0 12px 0;
    color: var(--rf-text-muted, #4b5563);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .segmented-group {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    background: var(--rf-bg-canvas, #f8f9fa);
    padding: 6px;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .segment-btn {
    padding: 10px 12px;
    font-size: 0.85rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    transition: all 0.12s ease;
  }

  .segment-btn:hover:not(.active) {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .segment-btn.active {
    background: var(--rf-color-yellow, #ffb703);
    color: #121212;
    font-weight: 900;
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .theme-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }

  .theme-card {
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    border-radius: var(--rf-border-radius, 0px);
    padding: 14px;
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 10px;
    text-align: left;
    transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
  }

  .theme-card:hover:not(.active) {
    transform: translate(-2px, -2px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .theme-card.active {
    border-color: var(--rf-border-color, #121212);
    outline: 2px solid var(--rf-accent-primary, #e63946);
    outline-offset: 2px;
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
    background: var(--rf-bg-card, #ffffff);
  }

  .theme-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .theme-card-title {
    font-size: 0.95rem;
    font-weight: 800;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .active-tag {
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    padding: 2px 6px;
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    border: 1px solid var(--rf-border-color, #121212);
  }

  .theme-desc {
    font-size: 0.8rem;
    color: var(--rf-text-muted, #4b5563);
    margin: 0;
    line-height: 1.35;
  }

  .swatch-group {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: auto;
  }

  .swatch-chip {
    width: 18px;
    height: 18px;
    border: 1px solid var(--rf-border-color, #121212);
    box-sizing: border-box;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-label {
    font-size: 0.82rem;
    font-weight: 700;
  }

  .form-select {
    padding: 8px 12px;
    font-size: 0.85rem;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    background: var(--rf-bg-surface, #ffffff);
    color: var(--rf-text-primary, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .modal-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: var(--rf-bg-canvas, #f8f9fa);
    border-top: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
  }

  .status-text {
    font-size: 0.75rem;
    color: var(--rf-text-muted, #4b5563);
    font-weight: 600;
  }

  .done-btn {
    padding: 8px 18px;
    font-size: 0.85rem;
    font-weight: 800;
    background: var(--rf-color-yellow, #ffb703);
    color: #121212;
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #121212);
    box-shadow: var(--rf-shadow-sm, 2px 2px 0px #121212);
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .done-btn:hover {
    transform: translate(-1px, -1px);
    box-shadow: var(--rf-shadow, 4px 4px 0px #121212);
  }

  .done-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 0px 0px 0px #121212;
  }
`;
