import { css } from 'lit';

export const homebrewFormStyles = css`
  .action-btn {
    background: #ffb703;
    color: #121212;
    border: 2px solid #121212;
    padding: 8px 16px;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 2px 2px 0px #121212;
    text-transform: uppercase;
  }
  .action-btn:hover { background: #fca311; }
  .action-btn.primary { background: #d90429; color: #ffffff; }
  .action-btn.primary:hover { background: #b70020; }
  .action-btn.secondary { background: #e2eafc; }
  .stat-block-expanded {
    border: 2px solid #121212;
    background: #fffdf0;
    padding: 14px;
    box-shadow: 4px 4px 0px #121212;
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 4px;
    text-align: center;
    background: #ffffff;
    border: 1px solid #121212;
    padding: 6px;
  }
  .stat-cell-title {
    font-size: 0.65rem;
    font-weight: 800;
  }
  .stat-cell-val {
    font-size: 0.85rem;
    font-weight: 700;
  }
  .form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .form-label {
    font-size: 0.78rem;
    font-weight: 800;
    text-transform: uppercase;
  }
  .form-input, .form-select, .form-textarea {
    padding: 6px 10px;
    font-family: inherit;
    font-size: 0.85rem;
    border: 2px solid #121212;
    box-shadow: 2px 2px 0px #121212;
    box-sizing: border-box;
  }
  .form-textarea {
    resize: vertical;
    min-height: 60px;
  }
  .form-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
`;
