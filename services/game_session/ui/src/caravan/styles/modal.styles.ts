import { css } from 'lit';

export const modalStyles = css`
  * { box-sizing: border-box; }

  .modal-backdrop {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.7); display: flex; align-items: center;
    justify-content: center; z-index: 1000; padding: 16px;
  }

  .manifest-modal {
    background: #ffffff; border: 3px solid #0f172a; box-shadow: 8px 8px 0px #0f172a;
    max-width: 620px; width: 100%; max-height: 85vh; overflow-y: auto; padding: 20px;
  }

  .modal-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 14px;
  }
  .modal-header h3 { margin: 0; font-size: 1.15rem; font-weight: 800; text-transform: uppercase; }

  .close-btn {
    background: #ffffff; border: 2px solid #0f172a; box-shadow: 2px 2px 0px #0f172a;
    font-size: 1.1rem; font-weight: 800; cursor: pointer; line-height: 1; padding: 2px 8px;
  }

  .modal-section { margin-bottom: 14px; }
  .modal-section-title {
    font-size: 0.8rem; font-weight: 800; text-transform: uppercase; color: #475569;
    margin-bottom: 6px; letter-spacing: 0.05em;
  }

  .route-summary-box {
    background: #f8fafc; border: 1.5px solid #0f172a; padding: 10px 14px;
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.85rem;
  }

  .cargo-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .cargo-pill {
    background: #ffffff; border: 1.5px solid #0f172a; box-shadow: 1px 1px 0px #0f172a;
    padding: 4px 10px; font-size: 0.8rem; font-weight: 700;
  }

  .ambush-log {
    background: #fef2f2; border: 1.5px solid #ef4444; padding: 10px 12px;
    font-size: 0.8rem; color: #7f1d1d; display: flex; flex-direction: column; gap: 6px;
  }
  .ambush-log-entry { border-bottom: 1px dashed #fca5a5; padding-bottom: 4px; }
  .ambush-log-entry:last-child { border-bottom: none; padding-bottom: 0; }

  .modal-footer {
    display: flex; justify-content: flex-end; gap: 10px; border-top: 2px solid #0f172a;
    padding-top: 14px; margin-top: 16px; flex-wrap: wrap;
  }

  .btn {
    padding: 6px 12px; font-weight: 700; font-size: 0.8rem; text-transform: uppercase;
    cursor: pointer; border: 2px solid #0f172a; box-shadow: 2px 2px 0px #0f172a; transition: all 0.1s ease;
  }
  .btn:active { transform: translate(1px, 1px); box-shadow: 1px 1px 0px #0f172a; }
  .btn-primary { background: #2563eb; color: #ffffff; }
  .btn-success { background: #16a34a; color: #ffffff; }
  .btn-warning { background: #f59e0b; color: #0f172a; }
  .btn-outline { background: #ffffff; color: #0f172a; }
`;
