export interface BulletinNoticeItem {
  notice_id: string;
  settlement_id: string;
  board_type: string;
  title: string;
  author_id: string;
  category: string;
  content: string;
  wax_sealed: boolean;
  cipher_encoded: boolean;
  cipher_puzzle?: string;
  cipher_hint?: string;
  hidden_content?: string | null;
  is_decrypted?: boolean;
  status?: string;
  created_at?: string;
}

export type BulletinBoardLocation = 'town_square' | 'tavern' | 'guildhall';
