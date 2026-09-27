/**
 * Types and interfaces for Campaign Dashboard and Creator components.
 * TASK-0209: Campaign Dashboard and Creation Microfrontend
 */

export type CampaignRole = 'owner' | 'dungeon_master' | 'dm' | 'player' | 'spectator';

export interface CampaignItem {
  id: string;
  title: string;
  description?: string;
  setting?: string;
  system?: string;
  status?: string;
  owner_id?: string;
  role?: CampaignRole | string;
  dm_name?: string;
  member_count?: number;
  player_count?: number;
  has_active_session?: boolean;
  active_session_id?: string | null;
  cover_image_url?: string | null;
  created_at?: string;
  updated_at?: string;
}

export type RoleFilter = 'all' | 'dming' | 'playing';

export interface CreateCampaignPayload {
  title: string;
  setting: string;
  system: string;
  cover_image_url?: string;
  description?: string;
}

export interface SelectCampaignEventDetail {
  campaignId: string;
  campaign: CampaignItem;
}
