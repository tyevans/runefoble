import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import '../styles/themes.css';
import '../components/runefoble-bulletin-board.ts';
import type { BulletinNoticeItem } from '../components/runefoble-bulletin-board.types.ts';

const mockNotices: BulletinNoticeItem[] = [
  {
    notice_id: 'ntc-001',
    settlement_id: 'stl-oakhaven-01',
    board_type: 'town_square',
    title: 'WANTED: Manticore of Wyvern Crag',
    author_id: 'Captain Varis',
    category: 'bounty',
    content:
      'A wounded manticore has descended from Wyvern Crag and harassed sheep caravans along the northern road. 250 gold pieces for proof of its defeat.',
    wax_sealed: false,
    cipher_encoded: false,
    status: 'active',
    created_at: '2026-09-27T10:00:00Z',
  },
  {
    notice_id: 'ntc-002',
    settlement_id: 'stl-oakhaven-01',
    board_type: 'town_square',
    title: 'Civic Curfew Ordinance',
    author_id: 'Mayor Aldous',
    category: 'ordinance',
    content:
      'By decree of the Town Council, tavern hearths must be dampened by the second bell of midnight. Night watch patrols will question anyone in back alleys.',
    wax_sealed: true,
    cipher_encoded: false,
    status: 'active',
    created_at: '2026-09-27T08:30:00Z',
  },
  {
    notice_id: 'ntc-003',
    settlement_id: 'stl-oakhaven-01',
    board_type: 'town_square',
    title: 'Lost Silver Pocket Watch',
    author_id: 'Elspeth the Baker',
    category: 'job',
    content:
      'Misplaced my grandfather engraved silver chronometer near the mill pond. Offering freshly baked honey tarts and 15 silver for its return.',
    wax_sealed: false,
    cipher_encoded: false,
    status: 'active',
    created_at: '2026-09-27T11:15:00Z',
  },
  {
    notice_id: 'ntc-004',
    settlement_id: 'stl-oakhaven-01',
    board_type: 'town_square',
    title: 'Whispers at the Rusty Anchor',
    author_id: 'Shadow Broker',
    category: 'rumor',
    content:
      'They say the smuggling skiff slips past the river bend when the fog bells toll three times. Seek the red lantern.',
    wax_sealed: false,
    cipher_encoded: true,
    cipher_puzzle: 'rot13',
    cipher_hint: 'Shift each thieves cant rune backwards by thirteen cycles...',
    hidden_content: 'Secret midnight rendezvous behind the barrel cellar. Ask for Jackdaw.',
    is_decrypted: false,
    status: 'active',
    created_at: '2026-09-27T12:00:00Z',
  },
];

const meta: Meta = {
  title: 'Settlements/RunefobleBulletinBoard',
  component: 'runefoble-bulletin-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const EmptyBoard: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc); min-height: 600px;">
      <runefoble-bulletin-board
        settlement-id="stl-oakhaven-01"
        settlement-name="Oakhaven Haven"
        board-type="town_square"
        .notices=${[]}
      ></runefoble-bulletin-board>
    </div>
  `,
};

export const PinnedNoticesTownSquare: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc); min-height: 600px;">
      <runefoble-bulletin-board
        settlement-id="stl-oakhaven-01"
        settlement-name="Oakhaven Crossroads"
        board-type="town_square"
        current-user-id="usr-adventurer"
        .notices=${mockNotices}
      ></runefoble-bulletin-board>
    </div>
  `,
};

export const CipherNoticeInspection: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc); min-height: 600px;">
      <runefoble-bulletin-board
        settlement-id="stl-oakhaven-01"
        settlement-name="Tavern Common Room"
        board-type="town_square"
        current-user-id="usr-rogue"
        .notices=${[mockNotices[3]]}
      ></runefoble-bulletin-board>
    </div>
  `,
};

export const WaxSealedProclamation: Story = {
  render: () => html`
    <div style="padding: 24px; background: var(--rf-bg-canvas, #f8fafc); min-height: 600px;">
      <runefoble-bulletin-board
        settlement-id="stl-oakhaven-01"
        settlement-name="Guildhall Plaza"
        board-type="town_square"
        current-user-id="usr-knight"
        .notices=${[mockNotices[1]]}
      ></runefoble-bulletin-board>
    </div>
  `,
};

export const DarkFantasyTheme: Story = {
  render: () => html`
    <div class="theme-dark-fantasy" style="padding: 24px; background: #09090b; min-height: 650px;">
      <runefoble-bulletin-board
        settlement-id="stl-oakhaven-01"
        settlement-name="Shadowed Haven Crossroads"
        board-type="town_square"
        current-user-id="usr-ranger"
        .notices=${mockNotices}
      ></runefoble-bulletin-board>
    </div>
  `,
};
