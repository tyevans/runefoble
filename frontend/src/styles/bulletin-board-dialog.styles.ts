import { css } from 'lit';

export const bulletinBoardDialogStyles = css`
  /* Modal Backdrop & Inspection Window */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(10, 5, 2, 0.75);
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 20px;
  }

  .parchment-modal {
    background: #fff9eb;
    background-image: linear-gradient(135deg, rgba(235, 220, 190, 0.4) 0%, rgba(255, 252, 245, 0.9) 100%);
    border: 2px solid #5c3a21;
    border-radius: 6px;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6);
    max-width: 560px;
    width: 100%;
    padding: 28px 24px;
    position: relative;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-close-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    background: none;
    border: none;
    font-size: 1.4rem;
    color: #5c3a21;
    cursor: pointer;
  }

  .cipher-mini-puzzle {
    background: #f4ecf8;
    border: 2px solid #8e44ad;
    border-radius: 6px;
    padding: 16px;
    margin: 16px 0;
  }

  .cipher-mini-puzzle h4 {
    margin: 0 0 6px 0;
    color: #5b2c6f;
  }

  .cipher-mini-puzzle p {
    margin: 0 0 10px 0;
    font-size: 0.85rem;
    color: #4a235a;
  }

  .cipher-input-row {
    display: flex;
    gap: 8px;
  }

  .cipher-input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #af7ac5;
    border-radius: 4px;
    font-family: inherit;
  }

  .cipher-submit-btn {
    background: #8e44ad;
    color: #fff;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
  }

  .revealed-secret {
    background: #e8f8f5;
    border: 2px solid #1abc9c;
    border-radius: 6px;
    padding: 14px;
    margin: 16px 0;
    color: #0e6251;
  }

  .revealed-secret h4 {
    margin: 0 0 4px 0;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 20px;
    border-top: 1px solid #d4b896;
    padding-top: 14px;
  }

  .danger-btn {
    background: #9b2226;
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
    cursor: pointer;
  }

  .secondary-btn {
    background: #5c3a21;
    color: white;
    border: none;
    padding: 6px 14px;
    border-radius: 4px;
    cursor: pointer;
  }
`;
