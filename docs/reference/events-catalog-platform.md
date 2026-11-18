# Reference: Events Catalog: Platform and Campaign Services

Part of the [Events Schema](events-schema.md). Each event identifier in this page is listed in [Event Identifiers](event-identifiers.md).

## Domain Event Catalog

### Campaign Analytics & Chronicle Events (`aggregate_type: CampaignChronicle`)

Aggregate state: `CampaignChronicleAggregate` (`services/campaign_analytics/src/campaign_analytics/aggregate.py`). Its aggregate id is a UUID v5 of the campaign id.

- **`ChronicleMilestoneRecorded`**: Recorded by `campaign_analytics` for each milestone and saved to the event store before its projection row is written (`runefoble.events.analytics.milestone_recorded`). Fields: `campaign_id_str`, `session_id_str`, `milestone_type`, `title`, `description`, `metadata`, `source_message_id`. Milestone identity: the timeline row id is the id of this saved event. `source_message_id` is `{stream}/{message_id}/{milestone_type}` of the stream message that caused it. A replay of that message finds the saved event by `source_message_id`, reuses its id and timestamp, and records no second event. The timeline therefore holds one row per milestone, even when a message is redelivered.
- **`CombatTelemetrySnapshotCreated`**: Defined, not produced by any service yet (`runefoble.events.analytics.telemetry_snapshot_created`). Fields: `campaign_id_str`, `session_id_str`, `total_damage`, `total_movements`, `active_combatants`.
- **`EncounterMvpAwarded`**: Defined, not produced by any service yet (`runefoble.events.analytics.mvp_awarded`). Fields: `campaign_id_str`, `session_id_str`, `encounter_id`, `combatant_id`, `combatant_name`, `award_title`, `metric_name`, `score`. MVP awards are computed at query time from `combat_performance_records`.

### Downtime, Crafting, Tavern Minigames & Merchant Haggling Events
For full schemas of `CraftingAttempted`, `CraftingSucceeded`, `CraftingMishapOccurred`, `CampfireRestCompleted`, `StrongholdCreated`, and `StrongholdUpgraded`, see [`downtime-and-crafting-events.md`](downtime-and-crafting-events.md).
For schemas of `MinigameStarted`, `MinigameTurnTaken`, `MinigameEnded`, `IntoxicationLevelChanged`, and `HagglingNegotiated`, see [`tavern-and-merchants-events.md`](tavern-and-merchants-events.md).

### West Marches & Cross-Campaign Trade Events (`aggregate_type: SharedWorld`, `CaravanLedger`)

- **`SharedWorldCreated`**: Emitted when a persistent West Marches shared frontier is established. Fields: `shared_world_id`, `name`, `frontier_region`, `description`, `created_by`.
- **`CampaignRegisteredToSharedWorld`**: Emitted when an adventuring campaign links into a shared world frontier. Fields: `shared_world_id`, `campaign_id`, `party_name`, `registered_by`.
- **`CrossCampaignDiscoveryShared`**: Emitted when an adventuring party maps a point of interest, dungeon, or waypoint. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `shared_world_id`, `discovery_id`, `name`, `discovery_type`, `coordinates`, `discovered_by_campaign_id`, `discovered_by_party_name`, `description`, `danger_level`, `metadata`.
- **`OutpostEstablished`**: Emitted when a regional settlement or base camp is established. Fields: `shared_world_id`, `outpost_id`, `name`, `region`, `level`, `facilities`, `contributing_campaign_id`, `resources_contributed`.
- **`SharedStrongholdUpgraded`**: Emitted when communal outpost facilities are upgraded. Fields: `shared_world_id`, `outpost_id`, `facility_id`, `new_tier`, `contributing_campaign_id`, `gold_spent`, `materials_spent`.
- **`CommunalNoticePosted`**: Emitted when a cross-campaign notice or bounty is posted to the tavern board. Fields: `shared_world_id`, `notice_id`, `campaign_id`, `author_name`, `title`, `content`, `notice_type`, `bounty_reward`.
- **`CaravanContractPosted`**: Emitted when an asynchronous mercenary caravan escort contract is posted to the frontier board (`CaravanContractPosted`). Fields: `contract_id`, `shared_world_id`, `origin_outpost`, `destination_outpost`, `cargo`, `cargo_value`, `route_risk_level`, `transit_stages`, `escort_collateral`, `reward_gold`, `reward_reputation`, `posted_by_campaign_id`, `poster_user_id`, `expires_in_turns`, `status`, `created_at`.
- **`CaravanContractAccepted`**: Emitted when an adventuring party claims or accepts an escort contract (`CaravanContractAccepted`). Fields: `contract_id`, `shared_world_id`, `contractor_campaign_id`, `contractor_party_name`, `accepted_by_user_id`, `status`, `accepted_at`.
- **`CaravanDispatched`**: Emitted when a resource caravan sets off across the frontier. Fields: `contract_id`, `shared_world_id`, `caravan_id`, `origin_outpost`, `destination_outpost`, `cargo`, `dispatched_by_campaign_id`, `transit_turns`, `status`.
- **`CaravanAmbushed`**: Emitted when a caravan encounters a wilderness hazard or ambush during transit stages (`CaravanAmbushed`). Fields: `contract_id`, `shared_world_id`, `caravan_id`, `stage_index`, `ambush_type`, `danger_level`, `outcome`, `cargo_loss_percentage`, `reported_by_campaign_id`, `notes`.
- **`CaravanTradeFulfilled`**: Emitted when a caravan successfully reaches destination, delivering cargo, unlocking settlement stock, and paying out rewards (`CaravanTradeFulfilled`). Fields: `contract_id`, `shared_world_id`, `caravan_id`, `origin_outpost`, `destination_outpost`, `cargo_delivered`, `cargo_value_delivered`, `reward_gold_paid`, `reputation_awarded`, `contractor_campaign_id`, `fulfilled_at`, `status`.
- **`CaravanTradeCompleted`**: Emitted when a caravan arrives at its destination outpost, unlocking regional merchant stock. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `shared_world_id`, `caravan_id`, `origin_outpost`, `destination_outpost`, `cargo_delivered`, `unlocked_stock`, `completed_at`.
- **`RegionalMerchantStockUpdated`**: Emitted when outpost merchant inventory adjusts due to trade or expeditions. Fields: `shared_world_id`, `outpost_name`, `inventory_updates`.

### Campaign Lifecycle, Membership & Invite Events (`aggregate_type: Campaign`, `CampaignMembership`, `CampaignInvite`, `CampaignSessions`)

Owned by `game_session` (ADR-0015 decision a). Defined in `libs/runefoble_events/src/runefoble_events/campaign_lifecycle.py`. The stream ID is the campaign UUID, except for `CampaignInvite`. There the stream ID is derived from a SHA-256 hash of the invite token, so the raw token never appears in the event store.

- **`CampaignCreated`**: Emitted when a campaign is created. The creator becomes owner. Fields: `campaign_id`, `owner_id`, `title`, `description`, `setting`, `system`, `cover_image_url`, `settings`.
- **`CampaignUpdated`**: Emitted when editable campaign fields change. Carries only the changed fields. Fields: `campaign_id`, `changes`.
- **`CampaignMemberAdded`**: Emitted when a user joins with a `player` or `spectator` role. Fields: `campaign_id`, `user_id`, `role`.
- **`CampaignMemberRemoved`**: Emitted when a member is removed. Fields: `campaign_id`, `user_id`.
- **`CampaignInviteCreated`**: Emitted when an invite is issued. Fields: `campaign_id`, `role`, `created_by`, `expires_at`, `max_uses`.
- **`CampaignInviteRedeemed`**: Emitted when a user redeems an invite. Fields: `campaign_id`, `user_id`.
- **`CampaignSessionCreated`**: Emitted when a session or staging lobby is added to a campaign. Fields: `campaign_id`, `session_id`, `title`, `status`, `scheduled_at`, `description`.

### User Profile Events (`aggregate_type: UserProfile`)

Owned by `game_session` (ADR-0015 decision a, TASK-0742). Defined in `libs/runefoble_events/src/runefoble_events/user_profile.py`. The stream ID is a UUID derived from the Zitadel subject, so one user has one profile stream.

- **`ProfileUpdated`**: Emitted when a user edits profile attributes. Carries only the changed fields. Fields: `subject`, `changes` (any of `display_name`, `avatar_url`, `bio`, `email`).

### Cross-Campaign Settlement & Haven Events (`aggregate_type: Settlement`)

- **`SettlementFoundedEvent`** (`runefoble.events.game_session.settlement_founded` / `SettlementFounded`): Emitted when a new settlement haven is founded with scale (hamlet, village, market town, city, metropolis), biome, coordinates, and initial district zoning. Fields: `settlement_id`, `campaign_id`, `name`, `scale`, `biome`, `coordinates`, `tier`, `prosperity`, `unlocked_districts`, `founded_by`, `metadata`.
- **`SettlementTierUpgradedEvent`** (`runefoble.events.game_session.settlement_tier_upgraded` / `SettlementTierUpgraded`): Emitted when a settlement accumulates sufficient civic prosperity and advances to a higher scale tier, unlocking specialized districts. Fields: `settlement_id`, `old_tier`, `new_tier`, `unlocked_districts`, `scale`, `prosperity`, `metadata`.
- **`SettlementCharteredEvent`** (`runefoble.events.game_session.settlement_chartered`): Emitted when a new frontier outpost, communal haven, or fortress is chartered. Fields: `settlement_id`, `shared_world_id`, `name`, `settlement_type`, `region`, `coordinates`, `founded_by_campaign_id`, `chartered_by`, `level`, `defense_rating`, `facilities`, `metadata`.
- **`SettlementResourcesDepositedEvent`** (`runefoble.events.game_session.settlement_resources_deposited`): Emitted when a manager adds gold and materials to a haven treasury. Fields: `settlement_id`, `shared_world_id`, `gold`, `materials`, `deposited_by`.
- **`SettlementUpgradedEvent`** (`runefoble.events.game_session.settlement_upgraded`): Emitted when a settlement facility (workshop, sanctum, fortifications, watchtower) or defense rating is upgraded. Fields: `settlement_id`, `shared_world_id`, `facility_id`, `new_tier`, `tier_name`, `contributing_campaign_id`, `gold_spent`, `materials_spent`, `defense_rating`, `metadata`.
- **`SettlementRestBoonClaimedEvent`** (`runefoble.events.game_session.settlement_rest_boon_claimed`): Emitted when an adventuring party or character claims a sanctum rest boon or workshop crafting perk. Fields: `settlement_id`, `shared_world_id`, `campaign_id`, `character_id`, `claimed_by`, `facility_id`, `boon`, `metadata`.
- **`BulletinNoticePinnedEvent`** (`runefoble.events.game_session.bulletin_notice_pinned` / `BulletinNoticePinned`): Emitted when a new notice, bounty, rumor, ordinance, or job is pinned to a settlement bulletin board (town square, tavern, or guildhall). Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `notice_id`, `settlement_id`, `board_type`, `title`, `author_id`, `category`, `content`, `wax_sealed`, `cipher_encoded`, `cipher_puzzle`, `cipher_solution`, `cipher_hint`, `hidden_content`, `metadata`.
- **`BulletinNoticeRemovedEvent`** (`runefoble.events.game_session.bulletin_notice_removed` / `BulletinNoticeRemoved`): Emitted when a notice is removed, fulfilled, or moderated from the bulletin board. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `notice_id`, `settlement_id`, `remover_id`, `reason`, `metadata`.
- **`CipherNoticeDecryptedEvent`** (`runefoble.events.game_session.cipher_notice_decrypted` / `CipherNoticeDecrypted`): Emitted when a player solves a coded cipher and unlocks secret quest text. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `notice_id`, `settlement_id`, `player_id`, `decrypted_content`, `metadata`.


### Establishment Domain Events (`aggregate_type: Establishment`)

- **`EstablishmentConstructedEvent`** (`runefoble.events.game_session.establishment_constructed` / `EstablishmentConstructed`): Emitted when a new commercial, civic, faith, underworld, or hospitality establishment is constructed in a zoned settlement district. Fields: `establishment_id`, `settlement_id`, `district_id`, `category`, `name`, `campaign_id`, `tier`, `capacity`, `operating_cost`, `amenities`, `owner_id`, `metadata`.
- **`EstablishmentUpgradedEvent`** (`runefoble.events.game_session.establishment_upgraded` / `EstablishmentUpgraded`): Emitted when an establishment advances in tier, expanding patron capacity, operating costs, and amenities. Fields: `establishment_id`, `settlement_id`, `tier`, `added_amenities`, `capacity`, `operating_cost`, `metadata`.
- **`EstablishmentOperationsUpdatedEvent`** (`runefoble.events.game_session.establishment_operations_updated` / `EstablishmentOperationsUpdated`): Emitted when active staff, total wages, and projected service quality update. Fields: `establishment_id`, `staff`, `total_wages`, `projected_service_quality`, `service_quality_tier`, `interpersonal_tension_index`, `metadata`.

### Assignable NPC Worker & Social Graph Events (`aggregate_type: NPCWorker`)

- **`NPCWorkerAssigned`** (`runefoble.events.game_session.npc_worker_assigned` / `NPCWorkerAssignedEvent`): Emitted when an NPC is hired or assigned to a role in an establishment storefront. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `npc_id`, `establishment_id`, `role`, `wage`, `assigned_at`, `name`, `campaign_id`, `traits`, `vices`, `trade_proficiencies`, `shelf_inventory`, `backroom_inventory`, `patience`, `metadata`.
- **`NPCWorkerRelieved`** (`runefoble.events.game_session.npc_worker_relieved` / `NPCWorkerRelievedEvent`): Emitted when an NPC worker is relieved, dismissed, or fired from an establishment. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `npc_id`, `establishment_id`, `reason`, `metadata`.
- **`NPCMoodUpdated`** (`runefoble.events.game_session.npc_mood_updated` / `NPCMoodUpdatedEvent`): Emitted when an NPC worker's mood, temperament, or patience shifts. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `npc_id`, `mood`, `temperament`, `patience_delta`, `metadata`.
- **`NPCRelationshipFormed`** (`runefoble.events.game_session.npc_relationship_formed` / `NPCRelationshipFormedEvent`): Emitted when an interpersonal social or supply tie is established between NPCs. Broadcast on Redis Stream `runefoble.events.west_marches`. Fields: `source_npc_id`, `target_npc_id`, `relation_type`, `intensity`, `notes`, `metadata`.


### Frontier Mercenary Bounty & Retrieval Contract Events (`aggregate_type: MercenaryBounty`)

- **`MercenaryBountyPosted`** (`MercenaryBountyPosted`): Emitted when a new mercenary bounty or retrieval contract is posted to the notice board with locked escrow. Broadcast on Redis Stream `runefoble.events.session`. Fields: `bounty_id`, `session_id`, `campaign_id`, `title`, `description`, `target_type`, `target_name`, `target_quantity`, `escrow_gold`, `escrow_items`, `poster_user_id`, `created_at`.
- **`MercenaryBountyClaimed`** (`MercenaryBountyClaimed`): Emitted when an adventuring party claims an active bounty. Broadcast on Redis Stream `runefoble.events.session`. Fields: `bounty_id`, `session_id`, `claimant_user_id`, `claimant_campaign_id`, `claimant_party_name`, `claimed_at`.
- **`MercenaryBountyFulfilled`** (`MercenaryBountyFulfilled`): Emitted when fulfillment proof is submitted, disputed, or completed with released escrow payout. Broadcast on Redis Stream `runefoble.events.session`. Fields: `bounty_id`, `session_id`, `proof`, `status`, `payout_gold`, `payout_items`, `fulfilled_by`, `fulfilled_at`.

### Dynamic FastMCP Tool Events (`aggregate_type: DynamicTool`)

- **`DynamicToolRegisteredEvent`** (`DynamicToolRegistered`): Emitted when a dynamic FastMCP tool is registered or hot-reloaded at runtime. Broadcast on Redis Stream `runefoble.events.system`. Fields: `tool_name`, `description`, `parameters`, `author_id`, `campaign_id`, `metadata`.
- **`DynamicToolUnregisteredEvent`** (`DynamicToolUnregistered`): Emitted when a dynamic tool is unregistered or retired from discovery. Broadcast on Redis Stream `runefoble.events.system`. Fields: `tool_name`, `unregistered_by`, `campaign_id`.
- **`DynamicToolInvokedEvent`** (`DynamicToolInvoked`): Emitted when an agent or user invokes a dynamic tool via FastMCP or REST frontdoors. Broadcast on Redis Stream `runefoble.events.system`. Fields: `tool_name`, `user_id`, `session_id`, `campaign_id`, `arguments`, `duration_ms`, `success`, `error`.


