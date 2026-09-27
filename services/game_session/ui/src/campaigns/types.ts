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

export interface CampaignMember {
  user_id: string;
  username: string;
  avatar_url?: string;
  character_name?: string;
  role: CampaignRole | string;
  subject_type?: string;
  zanzibar_relation?: string;
  joined_at?: string;
}

export interface AssignRoleEventDetail {
  campaignId: string;
  userId: string;
  role: 'dungeon_master' | 'player' | 'spectator' | string;
}

export interface RemoveMemberEventDetail {
  campaignId: string;
  userId: string;
}

export interface CreateInviteEventDetail {
  campaignId: string;
  role: 'player' | 'spectator';
  expiresInHours?: number;
  maxUses?: number;
}
