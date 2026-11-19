/**
 * Owner wire fixtures (TASK-0867).
 *
 * Each fixture uses the field names of the owner model named in its comment.
 * Keep these in step with the owner models. A fixture that drifts from the wire
 * hides the bug the App Shell must catch.
 */

/** ParticipantState (services/game_session/src/game_session/models/session.py:13). Keyed by player id. */
export const OWNER_PARTICIPANTS = {
  'user-fixture': {
    player_id: 'user-fixture', character_id: 'char-valeros', character_name: 'Valeros of Korvosa',
    character_class: 'Fighter', is_present: true, is_stand_in_active: false,
  },
  'user-kyra': {
    player_id: 'user-kyra', character_id: 'char-kyra', character_name: 'Kyra the Sun Maiden',
    character_class: 'Cleric', is_present: false, is_stand_in_active: false,
  },
};

/**
 * GameSessionState (services/game_session/src/game_session/models/session.py:22).
 * The owner names the identifier `session_id` and the round `combat_round`.
 */
export const OWNER_SESSION_STATE = {
  session_id: 'session-tomb-14',
  campaign_id: '4',
  title: 'Session #14: Tomb of the Star-Eater',
  dm_id: 'user-dm',
  status: 'active',
  current_turn: 1,
  participants: OWNER_PARTICIPANTS,
  active_character_id: null,
  stand_in_actions: [],
  in_combat: true,
  combat_round: 3,
  initiative_order: [],
  combat_active_id: null,
  combat_turn_started: false,
  turn_paused_for_reaction: false,
  active_reaction: null,
  ready_actions: [],
  lobby_readiness: { 'user-fixture': true },
  lobby_characters: { 'user-fixture': 'char-valeros' },
  atmosphere: null,
  weather: null,
  dm_overrides: [],
};

/** CampaignMemberResponse (services/game_session/src/game_session/campaign/schemas.py:89). */
export const OWNER_CAMPAIGN_MEMBERS = [
  { user_id: 'user-fixture', role: 'owner', subject_type: 'user', zanzibar_relation: 'owner', username: 'Valeros', character_name: 'Valeros of Korvosa' },
  { user_id: 'user-kyra', role: 'player', subject_type: 'user', zanzibar_relation: 'player', username: 'Kyra', character_name: 'Kyra the Sun Maiden' },
];

/** PlacedTokenState (services/board_state/src/board_state/models/tokens.py:10). Keyed by token id. */
export const OWNER_BOARD_TOKENS = {
  'tok-valeros': {
    token_id: 'tok-valeros', name: 'Valeros', token_type: 'pc', x: 2, y: 3, hp: 38, is_friendly: true,
    vision_radius: 4, active_hazard: null, hazard_status: null, active_action: null,
  },
  'tok-ghoul-1': {
    token_id: 'tok-ghoul-1', name: 'Ghoul', token_type: 'monster', x: 7, y: 6, hp: null, is_friendly: false,
    vision_radius: 2, active_hazard: null, hazard_status: null, active_action: 'attack',
  },
};

/** BoardState (services/board_state/src/board_state/models/board.py:18). */
export const OWNER_BOARD_STATE = {
  board_id: '6d0c3b1e-2f4a-4c59-9a8e-1f2b3c4d5e6f',
  session_id: 'session-tomb-14',
  cols: 12,
  rows: 10,
  tokens: OWNER_BOARD_TOKENS,
  terrain_cells: {},
  active_hazards: [],
  active_decals: [],
  fog_of_war_enabled: true,
  revealed_cells: [],
  background_asset_id: null,
  background_image_url: null,
};

/**
 * CaravanContractState (services/game_session/src/game_session/caravan/models.py:13).
 * The contracts endpoint returns a list of these (routers/caravan_contracts/board.py:113).
 */
export const OWNER_CARAVAN_CONTRACT = {
  contract_id: 'contract-1', shared_world_id: 'world-1', origin_outpost: 'Frontier Gate',
  destination_outpost: 'Ashen Keep', cargo: { grain: 4 }, cargo_value: 120, route_risk_level: 'medium',
  transit_stages: 2, current_stage: 0, escort_collateral: 0, reward_gold: 300, reward_reputation: 2,
  posted_by_campaign_id: '4', status: 'open', ambush_history: [], cargo_loss_percentage: 0,
  cargo_delivered: {}, cargo_value_delivered: 0, reward_gold_paid: 0, reputation_awarded: 0,
  expires_in_turns: 10, created_at: null, accepted_at: null, fulfilled_at: null,
};
