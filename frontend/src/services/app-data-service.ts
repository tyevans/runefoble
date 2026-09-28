import type { CampaignItem, CampaignMember, CreateCampaignPayload } from '@runefoble/game-session-ui';
import type { LobbyParticipant, LobbyCharacterOption } from '@runefoble/game-session-ui';
import type { CharacterItem, RosterCampaignOption } from '@runefoble/character-sheet-ui';
import type { BoardToken } from '@runefoble/board-state-ui';
import type { WatcherFeedEvent } from '@runefoble/the-watcher-ui';
import type { CampaignSessionItem } from '../components/runefoble-session-list.ts';
import { authService } from '../auth/auth-service.ts';

export const FALLBACK_CAMPAIGNS: CampaignItem[] = [
  {
    id: '4',
    title: 'Tomb of the Star-Eater',
    description: 'Ancient celestial horrors slumber beneath the irradiated astral sands.',
    setting: 'Spelljammer Astral Void',
    system: '5e',
    role: 'owner',
    owner_id: 'user-valeros',
    dm_name: 'The Watcher',
    player_count: 4,
    has_active_session: true,
    active_session_id: 'session-tomb-14',
  },
  {
    id: '5',
    title: 'Whispering Depths',
    description: 'Subterranean aquatic expeditions through forgotten dwarven aqueducts.',
    setting: 'Underdark Aquatics',
    system: '5e',
    role: 'player',
    owner_id: 'user-evelyn',
    dm_name: 'Evelyn Vance',
    player_count: 5,
    has_active_session: false,
  },
];

export const FALLBACK_CHARACTERS: CharacterItem[] = [
  {
    id: 'char-valeros',
    name: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    subclass: 'Battle Master',
    level: 4,
    currentHp: 38,
    maxHp: 45,
    armorClass: 18,
    speed: 30,
    campaignId: '4',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-kyra',
    name: 'Kyra the Sun Maiden',
    characterClass: 'Cleric',
    subclass: 'Life Domain',
    level: 4,
    currentHp: 28,
    maxHp: 32,
    armorClass: 16,
    speed: 25,
    campaignId: '4',
    campaignTitle: 'Tomb of the Star-Eater',
    portraitUrl: '/assets/portraits/cleric.svg',
  },
  {
    id: 'char-ezren',
    name: 'Ezren the Gray',
    characterClass: 'Wizard',
    subclass: 'Evocation',
    level: 5,
    currentHp: 22,
    maxHp: 26,
    armorClass: 12,
    speed: 30,
    campaignId: null,
    campaignTitle: null,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
];

export class AppDataService {
  private static instance: AppDataService;
  public apiBase = '/api/v1';

  static getInstance(): AppDataService {
    if (!AppDataService.instance) AppDataService.instance = new AppDataService();
    return AppDataService.instance;
  }

  private getAuthHeaders(): HeadersInit {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = authService.getAccessToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const user = authService.getUser();
    if (user?.user_id) headers['X-User-Id'] = user.user_id;
    return headers;
  }

  async fetchCampaigns(): Promise<CampaignItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [...FALLBACK_CAMPAIGNS];
  }

  async fetchCampaign(campaignId: string): Promise<CampaignItem | null> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return FALLBACK_CAMPAIGNS.find((c) => c.id === campaignId) || {
      id: campaignId,
      title: `Campaign #${campaignId}`,
      role: 'player',
      player_count: 3,
      has_active_session: false,
    };
  }

  async fetchCampaignMembers(campaignId: string): Promise<CampaignMember[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}/members`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [
      { user_id: 'user-valeros', username: 'Valeros (You)', character_name: 'Valeros of Korvosa', role: 'owner' },
      { user_id: 'user-kyra', username: 'Kyra Sunfall', character_name: 'Kyra the Sun Maiden', role: 'player' },
      { user_id: 'user-merisiel', username: 'Merisiel Nightshadow', character_name: 'Merisiel', role: 'player' },
    ];
  }

  async fetchCampaignSessions(campaignId: string): Promise<CampaignSessionItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns/${campaignId}/sessions`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [
      {
        id: campaignId === '4' ? 'session-tomb-14' : `session-${campaignId}-1`,
        campaignId,
        title: campaignId === '4' ? 'Session #14: Tomb of the Star-Eater' : `Session #1 (${campaignId})`,
        status: 'active',
        round: 3,
        participantsCount: 4,
      },
      {
        id: `lobby-${campaignId}-2`,
        campaignId,
        title: 'Session #15: Chamber of Horrors',
        status: 'lobby',
        participantsCount: 3,
      },
    ];
  }

  async fetchSession(sessionId: string): Promise<CampaignSessionItem | null> {
    try {
      const res = await fetch(`${this.apiBase}/sessions/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        return {
          id: data.id || sessionId,
          campaignId: data.campaign_id || data.campaignId || '',
          title: data.title || (sessionId === '14' || sessionId === 'session-tomb-14' ? 'Session #14' : `Session #${sessionId}`),
          status: data.status || 'active',
          round: data.round || 1,
          participantsCount: Array.isArray(data.participants) ? data.participants.length : (data.participantsCount || 0),
        };
      }
    } catch { /* fallback */ }
    if (sessionId === '14' || sessionId === 'session-tomb-14') {
      return {
        id: sessionId,
        campaignId: '4',
        title: 'Session #14: Tomb of the Star-Eater',
        status: 'active',
        round: 3,
        participantsCount: 4,
      };
    }
    if (sessionId === '15' || sessionId.startsWith('lobby-')) {
      return {
        id: sessionId,
        campaignId: '4',
        title: sessionId === '15' ? 'Lobby 15' : 'Session #15: Chamber of Horrors',
        status: 'lobby',
        participantsCount: 3,
      };
    }
    return {
      id: sessionId,
      campaignId: '',
      title: `Session #${sessionId}`,
      status: 'active',
      round: 1,
      participantsCount: 3,
    };
  }

  async fetchCharacters(): Promise<CharacterItem[]> {
    try {
      const res = await fetch(`${this.apiBase}/characters`, { headers: this.getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    return [...FALLBACK_CHARACTERS];
  }

  async fetchRosterCampaignOptions(): Promise<RosterCampaignOption[]> {
    const campaigns = await this.fetchCampaigns();
    return campaigns.map((c) => ({ id: c.id, title: c.title }));
  }

  async fetchLobbyState(sessionId: string): Promise<{
    participants: LobbyParticipant[];
    availableCharacters: LobbyCharacterOption[];
  }> {
    try {
      const res = await fetch(`${this.apiBase}/sessions/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.participants) {
          return {
            participants: data.participants,
            availableCharacters: [
              { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', level: 4 },
              { id: 'char-kyra', name: 'Kyra the Sun Maiden', characterClass: 'Cleric', level: 4 },
            ],
          };
        }
      }
    } catch { /* fallback */ }

    return {
      participants: [
        {
          userId: 'user-valeros',
          username: 'Valeros',
          role: 'Fighter Lvl 4',
          characterId: 'char-valeros',
          characterName: 'Valeros of Korvosa',
          characterClass: 'Fighter',
          characterLevel: 4,
          isReady: true,
          isAbsent: false,
          onlineStatus: 'online',
        },
        {
          userId: 'user-kyra',
          username: 'Kyra',
          role: 'Cleric Lvl 4',
          characterId: 'char-kyra',
          characterName: 'Kyra the Sun Maiden',
          characterClass: 'Cleric',
          characterLevel: 4,
          isReady: false,
          isAbsent: true,
          onlineStatus: 'offline',
        },
      ],
      availableCharacters: [
        { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', level: 4 },
        { id: 'char-kyra', name: 'Kyra the Sun Maiden', characterClass: 'Cleric', level: 4 },
        { id: 'char-ezren', name: 'Ezren the Gray', characterClass: 'Wizard', level: 5 },
      ],
    };
  }

  async fetchBoardTokens(sessionId: string): Promise<BoardToken[]> {
    try {
      const res = await fetch(`${this.apiBase}/boards/${sessionId}`, { headers: this.getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data.tokens) return data.tokens;
      }
    } catch { /* fallback */ }
    return [
      { id: '1', name: 'Valeros', x: 2, y: 3, color: 'var(--rf-accent-secondary)', hp: 38, maxHp: 45, visionRadius: 2 },
      { id: '2', name: 'Kyra (AI)', x: 3, y: 3, isAiControlled: true, color: 'var(--rf-accent-primary)', hp: 28, maxHp: 32, visionRadius: 2 },
      { id: '3', name: 'Goblin Scout', x: 5, y: 1, isHostile: true, color: 'var(--rf-accent-tertiary)', hp: 7, maxHp: 12 },
      { id: '4', name: 'Red Dragon Wyrmling', x: 6, y: 5, isHostile: true, color: 'var(--rf-border-color)', hp: 52, maxHp: 75 },
    ];
  }

  async fetchSessionEvents(_sessionId: string): Promise<WatcherFeedEvent[]> {
    return [
      { id: '1', timestamp: '19:45:00', source: 'watcher_dm', speaker: 'The Watcher (AI DM)', text: 'Welcome back, adventurers.', actionType: 'dm_ruling' },
      { id: '2', timestamp: '19:45:20', source: 'player', speaker: 'Valeros', text: '"I ready my shield and move two steps forward."', actionType: 'speech' },
      { id: '3', timestamp: '19:45:30', source: 'stand_in', speaker: 'Kyra (AI Stand-in, Drunk)', text: '"Hah! No dragon can outwit Sarenrae finest vintner!"', actionType: 'speech' },
    ];
  }

  async createCampaign(payload: CreateCampaignPayload): Promise<CampaignItem> {
    try {
      const res = await fetch(`${this.apiBase}/campaigns`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (res.ok) return await res.json();
    } catch { /* fallback */ }
    const newCamp: CampaignItem = {
      id: `camp-${Date.now()}`,
      title: payload.title,
      description: payload.description,
      setting: payload.setting,
      system: payload.system || '5e',
      role: 'owner',
      player_count: 1,
      has_active_session: false,
    };
    FALLBACK_CAMPAIGNS.unshift(newCamp);
    return newCamp;
  }
}

export const appDataService = AppDataService.getInstance();
