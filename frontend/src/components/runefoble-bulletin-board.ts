import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { playPaperRustle } from './runefoble-bulletin-board.audio.ts';
import {
  type ModalContext,
  renderInspectModal,
  renderPinNoticeModal,
} from './runefoble-bulletin-board.modals.ts';
import { bulletinBoardStyles } from './runefoble-bulletin-board.styles.ts';
import type {
  BulletinBoardLocation,
  BulletinNoticeItem,
} from './runefoble-bulletin-board.types.ts';


export * from './runefoble-bulletin-board.types.ts';

@customElement('runefoble-bulletin-board')
export class RunefobleBulletinBoard extends LitElement {
  static styles = [bulletinBoardStyles];

  @property({ type: String, attribute: 'settlement-id' }) settlementId = '';
  @property({ type: String, attribute: 'settlement-name' }) settlementName = 'Oakhaven Haven';
  @property({ type: String, attribute: 'board-type' }) boardType: BulletinBoardLocation = 'town_square';
  @property({ type: String, attribute: 'current-user-id' }) currentUserId = '';
  @property({ type: Array }) notices: BulletinNoticeItem[] = [];

  @state() private selectedCategory = 'all';
  @state() private activeNoticeModal: BulletinNoticeItem | null = null;
  @state() private cipherInputSolution = '';
  @state() private cipherErrorMessage = '';
  @state() private isPinModalOpen = false;

  @state() private newTitle = '';
  @state() private newCategory = 'rumor';
  @state() private newContent = '';
  @state() private newWaxSealed = false;
  @state() private newCipherEncoded = false;
  @state() private newCipherSolution = '';
  @state() private newHiddenContent = '';

  private get filteredNotices(): BulletinNoticeItem[] {
    return this.notices.filter((n) => {
      const matchBoard = n.board_type.toLowerCase() === this.boardType.toLowerCase();
      const matchCat =
        this.selectedCategory === 'all' ||
        n.category.toLowerCase() === this.selectedCategory.toLowerCase();
      return matchBoard && matchCat;
    });
  }

  private handleSelectBoardType(type: BulletinBoardLocation) {
    this.boardType = type;
    this.dispatchEvent(new CustomEvent('board-type-changed', { detail: { boardType: type } }));
  }

  private handleOpenNotice(notice: BulletinNoticeItem) {
    playPaperRustle();
    this.activeNoticeModal = { ...notice };
    this.cipherInputSolution = '';
    this.cipherErrorMessage = '';
    this.dispatchEvent(new CustomEvent('notice-inspected', { detail: { notice } }));
  }

  private handleCloseModal() {
    this.activeNoticeModal = null;
    this.cipherInputSolution = '';
    this.cipherErrorMessage = '';
  }

  private handleBreakSeal() {
    if (!this.activeNoticeModal) return;
    playPaperRustle();
    this.activeNoticeModal = { ...this.activeNoticeModal, wax_sealed: false };
    this.dispatchEvent(
      new CustomEvent('wax-seal-broken', {
        detail: { noticeId: this.activeNoticeModal.notice_id },
      })
    );
  }

  private handleDecryptCipher() {
    if (!this.activeNoticeModal) return;
    const sol = this.cipherInputSolution.trim();
    if (!sol) {
      this.cipherErrorMessage = 'Please enter a cipher solution.';
      return;
    }

    this.dispatchEvent(
      new CustomEvent('cipher-decrypt-attempt', {
        detail: {
          noticeId: this.activeNoticeModal.notice_id,
          solution: sol,
        },
      })
    );

    this.activeNoticeModal = {
      ...this.activeNoticeModal,
      is_decrypted: true,
      hidden_content:
        this.activeNoticeModal.hidden_content ||
        'Revealed secret quest coordinates: Rendezvous at midnight behind the Gilded Serpent.',
    };
    this.cipherErrorMessage = '';
  }

  private handleRemoveNotice(noticeId: string) {
    this.dispatchEvent(new CustomEvent('notice-removed', { detail: { noticeId } }));
    this.notices = this.notices.filter((n) => n.notice_id !== noticeId);
    this.activeNoticeModal = null;
  }

  private handleCreateNotice(e: Event) {
    e.preventDefault();
    const newNotice: BulletinNoticeItem = {
      notice_id: `ntc_${Date.now().toString(36)}`,
      settlement_id: this.settlementId,
      board_type: this.boardType,
      title: this.newTitle,
      author_id: this.currentUserId || 'anonymous',
      category: this.newCategory,
      content: this.newContent,
      wax_sealed: this.newWaxSealed,
      cipher_encoded: this.newCipherEncoded,
      cipher_puzzle: 'rot13',
      cipher_hint: this.newCipherEncoded ? 'Rotational thieves cant cipher' : undefined,
      hidden_content: this.newCipherEncoded ? this.newHiddenContent : null,
      is_decrypted: !this.newCipherEncoded,
      status: 'active',
      created_at: new Date().toISOString(),
    };

    this.notices = [...this.notices, newNotice];
    this.isPinModalOpen = false;
    playPaperRustle();
    this.dispatchEvent(new CustomEvent('notice-pinned', { detail: { notice: newNotice } }));

    this.newTitle = '';
    this.newContent = '';
    this.newHiddenContent = '';
    this.newCipherSolution = '';
    this.newWaxSealed = false;
    this.newCipherEncoded = false;
  }

  private buildModalContext(): ModalContext {
    return {
      activeNoticeModal: this.activeNoticeModal,
      isPinModalOpen: this.isPinModalOpen,
      boardType: this.boardType,
      cipherInputSolution: this.cipherInputSolution,
      cipherErrorMessage: this.cipherErrorMessage,
      newTitle: this.newTitle,
      newCategory: this.newCategory,
      newContent: this.newContent,
      newWaxSealed: this.newWaxSealed,
      newCipherEncoded: this.newCipherEncoded,
      newCipherSolution: this.newCipherSolution,
      newHiddenContent: this.newHiddenContent,
      onCloseInspect: () => this.handleCloseModal(),
      onClosePin: () => {
        this.isPinModalOpen = false;
      },
      onBreakSeal: () => this.handleBreakSeal(),
      onDecryptCipher: () => this.handleDecryptCipher(),
      onRemoveNotice: (id: string) => this.handleRemoveNotice(id),
      onCreateNotice: (e: Event) => this.handleCreateNotice(e),
      onInputCipherSolution: (val: string) => {
        this.cipherInputSolution = val;
      },
      onInputNewTitle: (val: string) => {
        this.newTitle = val;
      },
      onInputNewCategory: (val: string) => {
        this.newCategory = val;
      },
      onInputBoardType: (val: string) => {
        this.boardType = val as BulletinBoardLocation;
      },
      onInputNewContent: (val: string) => {
        this.newContent = val;
      },
      onToggleNewWaxSealed: (val: boolean) => {
        this.newWaxSealed = val;
      },
      onToggleNewCipherEncoded: (val: boolean) => {
        this.newCipherEncoded = val;
      },
      onInputNewCipherSolution: (val: string) => {
        this.newCipherSolution = val;
      },
      onInputNewHiddenContent: (val: string) => {
        this.newHiddenContent = val;
      },
    };
  }

  render() {
    const boardTitles: Record<string, string> = {
      town_square: 'Crossroads Town Square Bulletin',
      tavern: 'Tavern Common Room Rumor Board',
      guildhall: 'Master Guildhall Contracts & Bounties',
    };

    const modalCtx = this.buildModalContext();

    return html`
      <div class="bulletin-board-container" data-testid="bulletin-board">
        <header class="board-header">
          <div class="board-title">
            <h2>${boardTitles[this.boardType] || 'Community Bulletin Board'}</h2>
            <p>${this.settlementName} · Persistent Haven Hub</p>
          </div>

          <div class="board-controls">
            <div class="tab-group" role="tablist">
              <button
                class="tab-btn ${this.boardType === 'town_square' ? 'active' : ''}"
                @click=${() => this.handleSelectBoardType('town_square')}
              >
                Town Square
              </button>
              <button
                class="tab-btn ${this.boardType === 'tavern' ? 'active' : ''}"
                @click=${() => this.handleSelectBoardType('tavern')}
              >
                Tavern
              </button>
              <button
                class="tab-btn ${this.boardType === 'guildhall' ? 'active' : ''}"
                @click=${() => this.handleSelectBoardType('guildhall')}
              >
                Guildhall
              </button>
            </div>

            <div class="filter-group">
              ${['all', 'bounty', 'rumor', 'ordinance', 'job'].map(
                (cat) => html`
                  <button
                    class="filter-btn ${this.selectedCategory === cat ? 'active' : ''}"
                    @click=${() => (this.selectedCategory = cat)}
                  >
                    ${cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </button>
                `
              )}
            </div>

            <button class="pin-action-btn" @click=${() => (this.isPinModalOpen = true)}>
              + Pin Notice
            </button>
          </div>
        </header>

        <main class="cards-grid">
          ${this.filteredNotices.length === 0
            ? html`
                <div class="empty-board-state" data-testid="empty-board">
                  <div class="empty-icon">📜</div>
                  <h3>No notices pinned yet</h3>
                  <p>The corkboard is clear. Be the first to pin a bounty or town rumor!</p>
                </div>
              `
            : this.filteredNotices.map(
                (notice) => html`
                  <article
                    class="notice-card"
                    data-testid="notice-card"
                    @click=${() => this.handleOpenNotice(notice)}
                  >
                    <div class="push-pin"></div>
                    <span class="category-badge category-${notice.category.toLowerCase()}">
                      ${notice.category}
                    </span>
                    ${notice.cipher_encoded
                      ? html`<span class="cipher-indicator" title="Cipher Encoded">🔒 Coded</span>`
                      : ''}
                    <h3 class="card-title">${notice.title}</h3>
                    <p class="card-snippet">${notice.content}</p>
                    ${notice.wax_sealed ? html`<div class="wax-seal-badge" title="Wax Sealed">RF</div>` : ''}
                    <footer class="card-footer">
                      <span>By ${notice.author_id}</span>
                      <span>${notice.board_type}</span>
                    </footer>
                  </article>
                `
              )}
        </main>

        ${renderInspectModal(modalCtx)}
        ${renderPinNoticeModal(modalCtx)}
      </div>
    `;
  }
}
