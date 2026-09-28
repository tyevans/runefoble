import { html, type TemplateResult } from 'lit';
import type { BulletinNoticeItem } from './runefoble-bulletin-board.types.ts';

export interface ModalContext {
  activeNoticeModal: BulletinNoticeItem | null;
  isPinModalOpen: boolean;
  boardType: string;
  cipherInputSolution: string;
  cipherErrorMessage: string;
  newTitle: string;
  newCategory: string;
  newContent: string;
  newWaxSealed: boolean;
  newCipherEncoded: boolean;
  newCipherSolution: string;
  newHiddenContent: string;
  onCloseInspect: () => void;
  onClosePin: () => void;
  onBreakSeal: () => void;
  onDecryptCipher: () => void;
  onRemoveNotice: (id: string) => void;
  onCreateNotice: (e: Event) => void;
  onInputCipherSolution: (val: string) => void;
  onInputNewTitle: (val: string) => void;
  onInputNewCategory: (val: string) => void;
  onInputBoardType: (val: string) => void;
  onInputNewContent: (val: string) => void;
  onToggleNewWaxSealed: (val: boolean) => void;
  onToggleNewCipherEncoded: (val: boolean) => void;
  onInputNewCipherSolution: (val: string) => void;
  onInputNewHiddenContent: (val: string) => void;
}

export function renderInspectModal(ctx: ModalContext): TemplateResult | typeof html {
  const notice = ctx.activeNoticeModal;
  if (!notice) return html``;

  return html`
    <div class="modal-backdrop" @click=${ctx.onCloseInspect}>
      <div class="parchment-modal" @click=${(e: Event) => e.stopPropagation()} data-testid="notice-modal">
        <button class="modal-close-btn" @click=${ctx.onCloseInspect}>×</button>
        <span class="category-badge category-${notice.category.toLowerCase()}">
          ${notice.category}
        </span>
        <h2>${notice.title}</h2>
        <p style="color: #78593d; font-size: 0.85rem; margin-top: -6px;">
          Posted by <strong>${notice.author_id}</strong> on ${notice.board_type}
        </p>
        <hr style="border: 0; border-top: 1px dashed #d4b896; margin: 14px 0;" />

        <p style="font-size: 1rem; line-height: 1.5; color: #2e1b0f;">
          ${notice.content}
        </p>

        ${notice.wax_sealed
          ? html`
              <div style="margin: 16px 0; display: flex; align-items: center; gap: 12px;">
                <div class="wax-seal-badge" style="position: static;">RF</div>
                <span>This proclamation is sealed with royal red wax.</span>
                <button class="secondary-btn" @click=${ctx.onBreakSeal}>Break Seal</button>
              </div>
            `
          : ''}

        ${notice.cipher_encoded && !notice.is_decrypted
          ? html`
              <div class="cipher-mini-puzzle" data-testid="cipher-mini-puzzle">
                <h4>🔒 Thieves' Cant / Rune Cipher Overlay</h4>
                <p>
                  ${notice.cipher_hint || 'A coded message is scrawled in rotational runes.'}
                </p>
                <div class="cipher-input-row">
                  <input
                    type="text"
                    class="cipher-input"
                    placeholder="Enter deciphered plaintext..."
                    .value=${ctx.cipherInputSolution}
                    @input=${(e: Event) => ctx.onInputCipherSolution((e.target as HTMLInputElement).value)}
                  />
                  <button class="cipher-submit-btn" @click=${ctx.onDecryptCipher}>
                    Decrypt
                  </button>
                </div>
                ${ctx.cipherErrorMessage
                  ? html`<p style="color: #9b2226; font-size: 0.8rem; margin-top: 6px;">
                      ${ctx.cipherErrorMessage}
                    </p>`
                  : ''}
              </div>
            `
          : ''}

        ${notice.is_decrypted && notice.hidden_content
          ? html`
              <div class="revealed-secret" data-testid="revealed-secret">
                <h4>🔓 Decrypted Secret Quest Proclamation:</h4>
                <p>${notice.hidden_content}</p>
              </div>
            `
          : ''}

        <div class="modal-actions">
          <button class="danger-btn" @click=${() => ctx.onRemoveNotice(notice.notice_id)}>
            Remove Notice
          </button>
          <button class="secondary-btn" @click=${ctx.onCloseInspect}>Close</button>
        </div>
      </div>
    </div>
  `;
}

export function renderPinNoticeModal(ctx: ModalContext): TemplateResult | typeof html {
  if (!ctx.isPinModalOpen) return html``;

  return html`
    <div class="modal-backdrop" @click=${ctx.onClosePin}>
      <div class="parchment-modal" @click=${(e: Event) => e.stopPropagation()}>
        <button class="modal-close-btn" @click=${ctx.onClosePin}>×</button>
        <h2>Pin New Notice</h2>
        <form @submit=${ctx.onCreateNotice}>
          <div style="margin-bottom: 12px;">
            <label style="display: block; font-weight: bold; margin-bottom: 4px;">Title</label>
            <input
              type="text"
              style="width: 100%; padding: 8px; font-family: inherit;"
              required
              .value=${ctx.newTitle}
              @input=${(e: Event) => ctx.onInputNewTitle((e.target as HTMLInputElement).value)}
            />
          </div>

          <div style="display: flex; gap: 12px; margin-bottom: 12px;">
            <div style="flex: 1;">
              <label style="display: block; font-weight: bold; margin-bottom: 4px;">Category</label>
              <select
                style="width: 100%; padding: 8px; font-family: inherit;"
                .value=${ctx.newCategory}
                @change=${(e: Event) => ctx.onInputNewCategory((e.target as HTMLSelectElement).value)}
              >
                <option value="rumor">Rumor</option>
                <option value="bounty">Bounty</option>
                <option value="ordinance">Ordinance</option>
                <option value="job">Job</option>
              </select>
            </div>
            <div style="flex: 1;">
              <label style="display: block; font-weight: bold; margin-bottom: 4px;">Board</label>
              <select
                style="width: 100%; padding: 8px; font-family: inherit;"
                .value=${ctx.boardType}
                @change=${(e: Event) => ctx.onInputBoardType((e.target as HTMLSelectElement).value)}
              >
                <option value="town_square">Town Square</option>
                <option value="tavern">Tavern</option>
                <option value="guildhall">Guildhall</option>
              </select>
            </div>
          </div>

          <div style="margin-bottom: 12px;">
            <label style="display: block; font-weight: bold; margin-bottom: 4px;">Public Content</label>
            <textarea
              rows="3"
              style="width: 100%; padding: 8px; font-family: inherit;"
              required
              .value=${ctx.newContent}
              @input=${(e: Event) => ctx.onInputNewContent((e.target as HTMLTextAreaElement).value)}
            ></textarea>
          </div>

          <div style="margin-bottom: 12px; display: flex; gap: 16px;">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input
                type="checkbox"
                .checked=${ctx.newWaxSealed}
                @change=${(e: Event) => ctx.onToggleNewWaxSealed((e.target as HTMLInputElement).checked)}
              />
              Wax Sealed Proclamation
            </label>

            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input
                type="checkbox"
                .checked=${ctx.newCipherEncoded}
                @change=${(e: Event) => ctx.onToggleNewCipherEncoded((e.target as HTMLInputElement).checked)}
              />
              Cipher Encoded Mini-Puzzle
            </label>
          </div>

          ${ctx.newCipherEncoded
            ? html`
                <div style="background: #f4ecf8; padding: 12px; border-radius: 4px; margin-bottom: 12px;">
                  <label style="display: block; font-weight: bold; margin-bottom: 4px;">
                    Cipher Solution (Plaintext)
                  </label>
                  <input
                    type="text"
                    style="width: 100%; padding: 6px; margin-bottom: 8px;"
                    placeholder="e.g. meet at midnight"
                    .value=${ctx.newCipherSolution}
                    @input=${(e: Event) => ctx.onInputNewCipherSolution((e.target as HTMLInputElement).value)}
                  />

                  <label style="display: block; font-weight: bold; margin-bottom: 4px;">
                    Hidden Secret Quest / Coordinates Text
                  </label>
                  <textarea
                    rows="2"
                    style="width: 100%; padding: 6px;"
                    placeholder="Secret text revealed after decryption..."
                    .value=${ctx.newHiddenContent}
                    @input=${(e: Event) => ctx.onInputNewHiddenContent((e.target as HTMLTextAreaElement).value)}
                  ></textarea>
                </div>
              `
            : ''}

          <div class="modal-actions">
            <button type="submit" class="pin-action-btn">Pin to Board</button>
            <button type="button" class="secondary-btn" @click=${ctx.onClosePin}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  `;
}
