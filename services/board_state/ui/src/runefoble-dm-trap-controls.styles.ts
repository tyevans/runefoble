import { css } from 'lit';

export const dmTrapControlsStyles = css`
  :host {
    display: block;
    font-family: var(--rf-font-family, system-ui, sans-serif);
    color: var(--rf-text-primary, #1a1a1a);
    background: var(--rf-bg-surface, #ffffff);
    border: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a1a1a);
    box-shadow: var(--rf-shadow, 4px 4px 0px #1a1a1a);
    padding: 12px;
    box-sizing: border-box;
  }
  .hud-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: var(--rf-border-width, 2px) solid var(--rf-border-color, #1a1a1a);
    padding-bottom: 8px;
    margin-bottom: 10px;
  }
  .dm-badge {
    background: var(--rf-accent-primary, #e63946);
    color: #ffffff;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 2px 6px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .title { font-size: 0.95rem; font-weight: 800; display: flex; align-items: center; gap: 6px; }
  .trap-palette { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 10px; }
  .trap-btn {
    display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 8px 4px;
    background: var(--rf-bg-surface, #ffffff); border: 2px solid var(--rf-border-color, #1a1a1a);
    cursor: pointer; font-size: 0.75rem; font-weight: 700; box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a1a1a);
  }
  .trap-btn.active { background: #fdf0ed; border-color: var(--rf-accent-primary, #e63946); }
  .controls-row {
    display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; font-size: 0.8rem;
  }
  .controls-row select, .controls-row input {
    border: 2px solid var(--rf-border-color, #1a1a1a); padding: 3px 6px; font-weight: 700; font-size: 0.75rem; background: #ffffff;
  }
  .danger-zone-preview {
    border: 2px dashed var(--rf-accent-primary, #e63946); background: rgba(230, 57, 70, 0.08);
    padding: 8px; margin-bottom: 10px; font-size: 0.75rem; display: flex; align-items: center; justify-content: space-between;
  }
  .danger-pulse {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--rf-accent-primary, #e63946); animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%, 100% { transform: scale(0.9); opacity: 0.7; } 50% { transform: scale(1.3); opacity: 1; } }
  .action-footer { display: flex; gap: 8px; }
  .btn-hud {
    flex: 1; background: var(--rf-bg-surface, #ffffff); border: 2px solid var(--rf-border-color, #1a1a1a);
    padding: 6px 10px; font-weight: 800; font-size: 0.75rem; cursor: pointer; box-shadow: var(--rf-shadow-sm, 2px 2px 0px #1a1a1a);
  }
  .btn-hud.primary { background: var(--rf-border-color, #1a1a1a); color: #ffffff; }
  .btn-hud.accent { background: var(--rf-accent-primary, #e63946); color: #ffffff; border-color: var(--rf-accent-primary, #e63946); }
`;
