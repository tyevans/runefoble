import { css } from 'lit';

export const appShellStyles = css`
  :host {
    display: block;
    min-height: 100vh;
    background-color: var(--rf-bg-canvas);
    color: var(--rf-text-primary);
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    padding: 24px;
    box-sizing: border-box;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .layout-grid {
    display: grid;
    grid-template-columns: 1fr 340px 420px;
    gap: 24px;
    align-items: start;
  }
  @media (max-width: 1280px) {
    .layout-grid { grid-template-columns: 1fr; }
  }

  .character-column { display: flex; flex-direction: column; gap: 16px; }
  .voice-container { margin-top: 24px; }

  .campaign-hub-layout {
    display: flex; flex-direction: column; gap: 20px;
    max-width: 1400px; margin: 0 auto; width: 100%;
  }

  .campaign-nav-tabs {
    display: flex; gap: 8px; overflow-x: auto;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding-bottom: 0; margin-top: 8px; margin-bottom: 12px;
  }

  .campaign-nav-tabs .nav-tab {
    display: inline-flex; align-items: center; padding: 10px 18px;
    font-size: 0.95rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
    color: var(--rf-text-muted); background: transparent;
    border: var(--rf-border-width, 2px) solid transparent; border-bottom: none;
    cursor: pointer; text-decoration: none; transition: all 0.15s ease-in-out;
    position: relative; bottom: -2px; border-radius: var(--rf-border-radius, 0px) var(--rf-border-radius, 0px) 0 0;
  }
  .campaign-nav-tabs .nav-tab:hover { color: var(--rf-text-primary); background: var(--rf-bg-surface); }
  .campaign-nav-tabs .nav-tab.active {
    color: var(--rf-accent-primary); background: var(--rf-bg-surface);
    border-color: var(--rf-border-color); border-bottom: 2px solid var(--rf-bg-surface); font-weight: 800;
  }

  .campaign-tab-content { min-height: 300px; }
  .campaign-detail-layout { display: flex; flex-direction: column; gap: 24px; }

  .profile-layout {
    padding: 32px; background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); max-width: 600px; margin: 24px auto;
  }

  .auth-fallback-view {
    padding: 48px; text-align: center; background: var(--rf-bg-surface);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); max-width: 600px; margin: 40px auto;
  }
  .auth-fallback-view h2 { font-size: 1.5rem; margin: 0 0 12px 0; color: var(--rf-text-primary); }
  .auth-fallback-view p { color: var(--rf-text-muted); margin-bottom: 24px; }

  .toast-notification {
    position: fixed; bottom: 24px; right: 24px; background: var(--rf-bg-surface);
    color: var(--rf-text-primary); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-left: 6px solid var(--rf-accent-primary); padding: 12px 20px; box-shadow: var(--rf-shadow);
    font-weight: 500; z-index: 1000;
  }

  .dm-party-inspector {
    display: flex; flex-direction: column; gap: 8px; padding: 12px;
    background: var(--rf-bg-surface); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); box-sizing: border-box;
  }
  .dm-badge {
    font-size: 0.75rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--rf-accent-primary);
  }
  .dm-character-switcher {
    padding: 6px 10px; font-size: 0.85rem; font-family: inherit;
    background: var(--rf-bg-canvas); color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    border-radius: var(--rf-border-radius, 0px); cursor: pointer;
  }

  .character-sheet-view {
    display: flex; flex-direction: column; gap: 20px;
    max-width: 1400px; margin: 0 auto; width: 100%;
  }

  .character-sheet-header-bar {
    display: flex; align-items: center; justify-content: flex-start; padding-bottom: 8px;
  }

  .back-to-roster-btn {
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--rf-bg-surface); color: var(--rf-text-primary);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow-sm); font-family: var(--rf-font-family, inherit);
    font-weight: 700; font-size: 0.9rem; padding: 8px 16px; cursor: pointer;
    border-radius: var(--rf-border-radius, 0px); transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.1s ease;
  }
  .back-to-roster-btn:hover { transform: translate(-1px, -1px); box-shadow: var(--rf-shadow); color: var(--rf-accent-primary); }
  .back-to-roster-btn:active { transform: translate(1px, 1px); box-shadow: none; }

  .absentee-modal-backdrop {
    position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65);
    z-index: 1000; display: flex; align-items: center; justify-content: center;
    padding: 16px; box-sizing: border-box; backdrop-filter: blur(2px);
  }
  .absentee-drawer, .absentee-recap-dialog {
    background: var(--rf-bg-surface); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    box-shadow: var(--rf-shadow); max-width: 680px; width: 100%;
    max-height: 90vh; overflow-y: auto; padding: 20px; box-sizing: border-box;
  }
  .modal-top-bar {
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;
  }
  .btn-close-modal {
    background: var(--rf-bg-surface); color: var(--rf-text-primary); border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    font-weight: 700; cursor: pointer; padding: 4px 10px; font-size: 0.85rem;
  }
  .btn-toggle-directive {
    background: var(--rf-accent-secondary); color: var(--rf-text-on-accent, var(--rf-bg-surface));
    border: var(--rf-border-width, 2px) solid var(--rf-border-color);
    padding: 6px 12px; font-weight: 700; cursor: pointer; font-size: 0.85rem;
    box-shadow: var(--rf-shadow-sm); margin-top: 8px;
  }
`;

