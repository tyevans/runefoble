import { css } from 'lit';

export const dmNegotiationDrawerStyles = css`
  :host {
    display: block;
    box-sizing: border-box;
    font-family: var(--rf-font-family, system-ui, -apple-system, sans-serif);
    color: var(--rf-text-primary, #0f172a);
  }

  * {
    box-sizing: border-box;
  }

  .dm-drawer {
    background: #1e1e24;
    color: #f8fafc;
    border: 3px solid #f59e0b;
    box-shadow: 4px 4px 0px #000000;
    max-width: 760px;
    margin: 0 auto;
    border-radius: 4px;
    overflow: hidden;
  }

  .drawer-header {
    background: #27272a;
    padding: 12px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #f59e0b;
  }

  .drawer-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .dm-badge {
    background: #dc2626;
    color: #ffffff;
    padding: 2px 6px;
    font-size: 0.7rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-radius: 2px;
  }

  .drawer-title h4 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  .status-tag {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 2px;
    text-transform: uppercase;
    background: #3b82f6;
    color: #ffffff;
  }

  .status-tag.completed {
    background: #10b981;
  }

  .status-tag.refused,
  .status-tag.terminated {
    background: #ef4444;
  }

  .drawer-body {
    padding: 16px 18px;
  }

  /* Live Telemetry Bar */
  .telemetry-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    background: #18181b;
    border: 1px solid #3f3f46;
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 2px;
  }

  .telemetry-item {
    font-size: 0.8rem;
  }

  .telemetry-label {
    color: #a1a1aa;
    font-weight: 600;
    margin-bottom: 2px;
  }

  .telemetry-value {
    font-size: 1.1rem;
    font-weight: 800;
    color: #fbbf24;
  }

  /* One-Click Modifiers */
  .section-label {
    font-size: 0.8rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #fbbf24;
    margin-bottom: 8px;
  }

  .modifier-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }

  .dm-btn {
    padding: 10px 14px;
    border: 2px solid #000000;
    font-weight: 800;
    font-size: 0.8rem;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 2px 2px 0px #000000;
    transition: all 0.1s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .dm-btn:hover {
    filter: brightness(1.1);
  }

  .dm-btn:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px #000000;
  }

  .btn-soothe {
    background: #10b981;
    color: #ffffff;
  }

  .btn-enrage {
    background: #ea580c;
    color: #ffffff;
  }

  .btn-accept {
    background: #2563eb;
    color: #ffffff;
  }

  .btn-refuse {
    background: #dc2626;
    color: #ffffff;
  }

  /* Custom Bark Injection Form */
  .bark-injection-box {
    background: #18181b;
    border: 1px solid #3f3f46;
    padding: 14px;
    border-radius: 2px;
  }

  .input-row {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  .bark-input {
    flex: 1;
    background: #27272a;
    border: 1px solid #52525b;
    color: #f8fafc;
    padding: 8px 12px;
    font-size: 0.85rem;
    font-family: inherit;
    border-radius: 2px;
  }

  .bark-input:focus {
    outline: none;
    border-color: #fbbf24;
  }

  .price-override-input {
    width: 90px;
    background: #27272a;
    border: 1px solid #52525b;
    color: #fbbf24;
    padding: 8px;
    font-weight: 800;
    text-align: right;
    border-radius: 2px;
  }

  .btn-broadcast {
    background: #f59e0b;
    color: #000000;
    font-weight: 800;
    border: 2px solid #000000;
    padding: 8px 14px;
    cursor: pointer;
    text-transform: uppercase;
    font-size: 0.8rem;
    box-shadow: 2px 2px 0px #000000;
  }
`;
