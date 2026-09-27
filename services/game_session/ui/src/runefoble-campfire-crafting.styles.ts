import { css } from 'lit';

export const campfireCraftingStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #1e293b);
    background: var(--rf-surface, #f8fafc);
    border: var(--rf-border-width, 3px) solid var(--rf-border-color, #0f172a);
    box-shadow: var(--rf-shadow-hard, 5px 5px 0px #0f172a);
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
  }

  * {
    box-sizing: border-box;
  }

  .header-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid var(--rf-border-color, #0f172a);
    padding-bottom: 16px;
    margin-bottom: 20px;
  }

  .title-group h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .title-group p {
    margin: 4px 0 0 0;
    color: var(--rf-text-muted, #64748b);
    font-size: 0.9rem;
  }

  .grid-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }

  @media (max-width: 768px) {
    .grid-layout {
      grid-template-columns: 1fr;
    }
  }

  /* Card Sections */
  .panel {
    background: var(--rf-surface-card, #ffffff);
    border: 2px solid var(--rf-border-color, #0f172a);
    padding: 16px;
    box-shadow: 3px 3px 0px var(--rf-border-color, #0f172a);
  }

  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    font-size: 1.1rem;
    font-weight: 700;
    text-transform: uppercase;
    border-bottom: 1px dashed var(--rf-border-color, #94a3b8);
    padding-bottom: 6px;
  }

  /* Campfire Atmosphere */
  .campfire-box {
    background: #fff7ed;
    border-color: #ea580c;
  }

  .prompt-quote {
    font-style: italic;
    background: #ffedd5;
    padding: 12px;
    border-left: 4px solid #f97316;
    margin: 10px 0;
    font-size: 0.95rem;
    line-height: 1.4;
  }

  .rest-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-top: 14px;
  }

  .rest-toggle {
    display: flex;
    border: 2px solid #0f172a;
  }

  .rest-toggle button {
    background: #ffffff;
    border: none;
    padding: 6px 14px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .rest-toggle button.active {
    background: #ea580c;
    color: #ffffff;
  }

  .btn {
    border: 2px solid #0f172a;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 0.9rem;
    cursor: pointer;
    box-shadow: 2px 2px 0px #0f172a;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
    text-transform: uppercase;
  }

  .btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #0f172a;
  }

  .btn-primary {
    background: var(--rf-primary, #3b82f6);
    color: #ffffff;
  }

  .btn-flame {
    background: #ea580c;
    color: #ffffff;
  }

  /* Reagents & Crucible */
  .reagents-tray {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 5px 10px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid #0f172a;
    cursor: pointer;
    user-select: none;
    box-shadow: 1px 1px 0px #0f172a;
    background: #f1f5f9;
  }

  .chip.selected {
    background: #dbeafe;
    border-color: #2563eb;
    box-shadow: 2px 2px 0px #2563eb;
  }

  .chip-radiant { background: #fef08a; }
  .chip-volatile { background: #fed7aa; }
  .chip-draconic { background: #fecaca; }
  .chip-toxic { background: #d9f99d; }
  .chip-arcane { background: #e9d5ff; }

  .crucible-chamber {
    background: #0f172a;
    color: #f8fafc;
    padding: 16px;
    border: 2px solid #0f172a;
    min-height: 110px;
    margin-bottom: 14px;
  }

  .crucible-title {
    font-size: 0.85rem;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .crucible-slots {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 10px;
  }

  .catalyst-selector {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
    font-size: 0.85rem;
  }

  .catalyst-selector select {
    padding: 4px 8px;
    border: 2px solid #0f172a;
    font-weight: 600;
  }

  /* Risk Meter */
  .risk-meter {
    margin-bottom: 14px;
  }

  .risk-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .risk-bar {
    height: 10px;
    background: #e2e8f0;
    border: 1px solid #0f172a;
    overflow: hidden;
  }

  .risk-fill {
    height: 100%;
    transition: width 0.3s ease;
  }

  .risk-fill.low { background: #22c55e; }
  .risk-fill.med { background: #eab308; }
  .risk-fill.high { background: #ef4444; }

  /* Outcome alert */
  .outcome-box {
    margin-top: 14px;
    padding: 12px;
    border: 2px solid #0f172a;
    box-shadow: 2px 2px 0px #0f172a;
  }

  .outcome-box.success {
    background: #dcfce7;
    border-color: #15803d;
  }

  .outcome-box.mishap {
    background: #fee2e2;
    border-color: #b91c1c;
  }

  /* Stronghold Facilities */
  .facility-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .facility-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
  }

  .facility-name {
    font-weight: 700;
    font-size: 0.9rem;
  }

  .facility-tier {
    font-size: 0.8rem;
    background: #0f172a;
    color: #ffffff;
    padding: 2px 6px;
    font-weight: 700;
  }

  .boons-tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }

  .boon-tag {
    background: #e0e7ff;
    color: #3730a3;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 8px;
    border: 1px solid #c7d2fe;
  }
`;
