"""Event-sourced Settlement Aggregate managing civic scales, districts, and haven charters.

Governed by ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.models import (
    DEFAULT_FACILITIES,
    DEFAULT_TIER_DISTRICTS,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    SCALE_MAX_DISTRICTS,
    SCALE_TO_TIER,
    TIER_MIN_PROSPERITY,
    TIER_TO_SCALE,
    BulletinNoticeState,
    SettlementScale,
    SettlementState,
)
from runefoble_events.settlements import (
    BulletinNoticePinnedEvent,
    BulletinNoticeRemovedEvent,
    CipherNoticeDecryptedEvent,
    SettlementCharteredEvent,
    SettlementFoundedEvent,
    SettlementRestBoonClaimedEvent,
    SettlementTierUpgradedEvent,
    SettlementUpgradedEvent,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class SettlementAggregate(DeclarativeAggregate[SettlementState]):
    """Event-sourced aggregate managing settlement layout, scaling, and havens."""

    aggregate_type = "Settlement"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = SettlementState(settlement_id=str(aggregate_id or ""))

    @handles(SettlementFoundedEvent)
    def handle_settlement_founded(self, ev: SettlementFoundedEvent) -> None:
        """Handle founding of a settlement haven."""
        scale_key = ev.scale.lower()
        tier = ev.tier or SCALE_TO_TIER.get(scale_key, 1)
        max_districts = SCALE_MAX_DISTRICTS.get(tier, 2)
        districts = (
            list(ev.unlocked_districts)
            if ev.unlocked_districts
            else list(DEFAULT_TIER_DISTRICTS.get(tier, []))
        )
        self._state.settlement_id = ev.settlement_id or str(ev.aggregate_id)
        self._state.campaign_id = str(ev.campaign_id)
        self._state.name = ev.name
        self._state.scale = scale_key
        self._state.tier = tier
        self._state.biome = ev.biome
        self._state.coordinates = dict(ev.coordinates)
        self._state.prosperity = max(self._state.prosperity, ev.prosperity)
        self._state.max_districts = max_districts
        self._state.districts = districts[:max_districts]
        self._state.chartered_by = ev.founded_by
        self._state.is_founded = True

    @handles(SettlementTierUpgradedEvent)
    def handle_tier_upgraded(self, ev: SettlementTierUpgradedEvent) -> None:
        """Handle settlement advancement to higher civic scale tier."""
        new_tier = int(ev.new_tier)
        new_scale = ev.scale or TIER_TO_SCALE.get(new_tier, self._state.scale)
        self._state.tier = new_tier
        self._state.scale = new_scale
        self._state.max_districts = SCALE_MAX_DISTRICTS.get(new_tier, 32)
        if ev.prosperity:
            self._state.prosperity = max(self._state.prosperity, ev.prosperity)
        for d in ev.unlocked_districts:
            if (
                d not in self._state.districts
                and len(self._state.districts) < self._state.max_districts
            ):
                self._state.districts.append(d)

    @handles(SettlementCharteredEvent)
    def handle_chartered(self, ev: SettlementCharteredEvent) -> None:
        """Handle legacy chartering for West Marches persistent frontier."""
        fac = dict(ev.facilities) if ev.facilities else dict(DEFAULT_FACILITIES)
        cid = [str(ev.founded_by_campaign_id)] if ev.founded_by_campaign_id else []
        self._state.settlement_id = ev.settlement_id or str(ev.aggregate_id)
        self._state.shared_world_id = ev.shared_world_id
        self._state.name = ev.name
        self._state.settlement_type = ev.settlement_type
        self._state.region = ev.region
        self._state.coordinates = dict(ev.coordinates)
        self._state.campaign_id = str(ev.founded_by_campaign_id)
        self._state.chartered_by = ev.chartered_by
        self._state.level = ev.level
        self._state.defense_rating = ev.defense_rating
        self._state.facilities = fac
        self._state.contributing_campaigns = cid
        self._state.active_boons = {k: FACILITY_REST_BOONS.get(k, "") for k in fac}
        self._state.is_founded = True

    @handles(SettlementUpgradedEvent)
    def handle_upgraded(self, event: SettlementUpgradedEvent) -> None:
        """Handle facility upgrades."""
        self._state.facilities[event.facility_id] = event.new_tier
        if event.facility_id in FACILITY_REST_BOONS:
            self._state.active_boons[event.facility_id] = FACILITY_REST_BOONS[event.facility_id]
        cid = str(event.contributing_campaign_id)
        if cid and cid not in self._state.contributing_campaigns:
            self._state.contributing_campaigns.append(cid)
        for mat, qty in event.materials_spent.items():
            self._state.materials_treasury[mat] = self._state.materials_treasury.get(mat, 0) + qty
        self._state.gold_invested += event.gold_spent
        if event.facility_id == "fortifications":
            self._state.defense_rating = max(self._state.defense_rating, event.defense_rating)
        self._state.level = max(1, max(self._state.facilities.values()))

    @handles(SettlementRestBoonClaimedEvent)
    def handle_boon_claimed(self, event: SettlementRestBoonClaimedEvent) -> None:
        """Handle claiming of rest boons."""
        self._state.active_boons[event.facility_id] = event.boon

    @handles(BulletinNoticePinnedEvent)
    def handle_bulletin_notice_pinned(self, ev: BulletinNoticePinnedEvent) -> None:
        """Handle pinning a new bulletin notice or bounty to the settlement board."""
        notice = BulletinNoticeState(
            notice_id=ev.notice_id,
            settlement_id=ev.settlement_id,
            board_type=ev.board_type,
            title=ev.title,
            author_id=ev.author_id,
            category=ev.category,
            content=ev.content,
            wax_sealed=ev.wax_sealed,
            cipher_encoded=ev.cipher_encoded,
            cipher_puzzle=ev.cipher_puzzle,
            cipher_solution=ev.cipher_solution,
            cipher_hint=ev.cipher_hint,
            hidden_content=ev.hidden_content,
            decrypted_by=[],
            status="active",
            created_at=str(ev.occurred_at or ""),
            metadata=dict(ev.metadata),
        )
        self._state.bulletin_notices[ev.notice_id] = notice

    @handles(BulletinNoticeRemovedEvent)
    def handle_bulletin_notice_removed(self, ev: BulletinNoticeRemovedEvent) -> None:
        """Handle removing or fulfilling a bulletin notice."""
        if ev.notice_id in self._state.bulletin_notices:
            self._state.bulletin_notices[ev.notice_id].status = "removed"

    @handles(CipherNoticeDecryptedEvent)
    def handle_cipher_notice_decrypted(self, ev: CipherNoticeDecryptedEvent) -> None:
        """Handle unlocking cipher secret for a player."""
        if ev.notice_id in self._state.bulletin_notices:
            notice = self._state.bulletin_notices[ev.notice_id]
            if ev.player_id and ev.player_id not in notice.decrypted_by:
                notice.decrypted_by.append(ev.player_id)

    def found(
        self,
        name: str,
        campaign_id: str,
        scale: str = SettlementScale.VILLAGE.value,
        biome: str = "river_confluence",
        coordinates: dict[str, float] | None = None,
        prosperity: int = 0,
        districts: list[str] | None = None,
        founded_by: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Found a new settlement haven with scale, biome, and initial zoning districts."""
        if self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has already been founded")

        scale_key = scale.lower()
        if scale_key not in SCALE_TO_TIER:
            valid = ", ".join(SCALE_TO_TIER.keys())
            raise ValueError(f"Invalid settlement scale '{scale}'. Must be one of: {valid}")

        tier = SCALE_TO_TIER[scale_key]
        max_districts = SCALE_MAX_DISTRICTS.get(tier, 2)

        if districts is not None:
            if len(districts) > max_districts:
                raise ValueError(
                    f"Scale '{scale}' permits at most {max_districts} districts, but {len(districts)} were specified"
                )
            initial_districts = list(districts)
        else:
            initial_districts = list(DEFAULT_TIER_DISTRICTS.get(tier, []))[:max_districts]

        sid = str(self.aggregate_id or uuid4())
        self.create_event(
            SettlementFoundedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            campaign_id=str(campaign_id),
            name=name,
            scale=scale_key,
            biome=biome,
            coordinates=coordinates or {},
            tier=tier,
            prosperity=prosperity,
            unlocked_districts=initial_districts,
            founded_by=founded_by,
            metadata=metadata or {},
        )
        return sid

    def upgrade_tier(
        self,
        new_tier: int | None = None,
        target_scale: str | None = None,
        prosperity: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Advance settlement scale tier if prerequisites are met."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")

        if new_tier is None and target_scale is not None:
            new_tier = SCALE_TO_TIER.get(target_scale.lower())

        if new_tier is None:
            new_tier = self._state.tier + 1

        expected_tier = self._state.tier + 1
        if new_tier != expected_tier:
            raise ValueError(
                f"Invalid tier upgrade: current tier is {self._state.tier}, can only advance to tier {expected_tier}"
            )

        if new_tier not in TIER_TO_SCALE:
            raise ValueError(
                f"Tier {new_tier} exceeds maximum settlement scale (Tier 5 - Metropolis)"
            )

        effective_prosperity = prosperity if prosperity is not None else self._state.prosperity
        min_prosperity = TIER_MIN_PROSPERITY.get(new_tier, 0)
        if effective_prosperity < min_prosperity:
            raise ValueError(
                f"Insufficient civic prosperity: {effective_prosperity} < required {min_prosperity} for tier {new_tier}"
            )

        unlocked = DEFAULT_TIER_DISTRICTS.get(new_tier, [])
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementTierUpgradedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            old_tier=self._state.tier,
            new_tier=new_tier,
            unlocked_districts=unlocked,
            scale=TIER_TO_SCALE[new_tier],
            prosperity=effective_prosperity,
            metadata=metadata or {},
        )
        return new_tier

    def charter(self, name: str, shared_world_id: str, **kw: Any) -> str:
        """Legacy charter for frontier havens."""
        sid = str(self.aggregate_id or uuid4())
        self.create_event(
            SettlementCharteredEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=str(shared_world_id),
            name=name,
            settlement_type=kw.get("settlement_type", "haven"),
            region=kw.get("region", "Wilderness"),
            coordinates=kw.get("coordinates") or {},
            founded_by_campaign_id=str(kw.get("founded_by_campaign_id", "")),
            chartered_by=kw.get("chartered_by", ""),
            level=1,
            defense_rating=kw.get("defense_rating", 10),
            facilities=kw.get("facilities") or dict(DEFAULT_FACILITIES),
            metadata=kw.get("metadata") or {},
        )
        return sid

    def upgrade_facility(
        self,
        facility_id: str,
        contributing_campaign_id: str = "",
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Upgrade haven facilities."""
        next_tier = self._state.facilities.get(facility_id, 0) + 1
        tier_name = FACILITY_TIER_NAMES.get(facility_id, {}).get(next_tier, f"Tier {next_tier}")
        new_def = self._state.defense_rating + (5 if facility_id == "fortifications" else 0)
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementUpgradedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=self._state.shared_world_id,
            facility_id=facility_id,
            new_tier=next_tier,
            tier_name=tier_name,
            contributing_campaign_id=str(contributing_campaign_id),
            gold_spent=gold_spent,
            materials_spent=materials_spent or {},
            defense_rating=new_def,
            metadata=metadata or {},
        )
        return next_tier

    def claim_rest_boon(
        self,
        campaign_id: str,
        character_id: str = "",
        claimed_by: str = "",
        facility_id: str = "sanctum",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Claim resting boons from settlement sanctum."""
        boon = FACILITY_REST_BOONS.get(
            facility_id, "Restful Refuge: Safe haven from wandering monsters."
        )
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementRestBoonClaimedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=self._state.shared_world_id,
            campaign_id=str(campaign_id),
            character_id=character_id,
            claimed_by=claimed_by,
            facility_id=facility_id,
            boon=boon,
            metadata=metadata or {},
        )
        return boon

    def pin_bulletin_notice(
        self,
        title: str,
        content: str,
        author_id: str,
        board_type: str = "town_square",
        category: str = "rumor",
        wax_sealed: bool = False,
        cipher_encoded: bool = False,
        cipher_puzzle: str = "rot13",
        cipher_solution: str = "",
        cipher_hint: str = "",
        hidden_content: str = "",
        notice_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Pin a notice, rumor, bounty, or job to the settlement notice board."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")

        nid = notice_id or f"ntc_{uuid4().hex[:12]}"
        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            BulletinNoticePinnedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=nid,
            settlement_id=sid,
            board_type=board_type,
            title=title,
            author_id=str(author_id),
            category=category,
            content=content,
            wax_sealed=wax_sealed,
            cipher_encoded=cipher_encoded,
            cipher_puzzle=cipher_puzzle,
            cipher_solution=cipher_solution,
            cipher_hint=cipher_hint,
            hidden_content=hidden_content,
            metadata=metadata or {},
        )
        return nid

    def remove_bulletin_notice(
        self,
        notice_id: str,
        remover_id: str = "",
        reason: str = "removed",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Remove or fulfill a notice from the bulletin board."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")
        if notice_id not in self._state.bulletin_notices:
            raise ValueError(f"Bulletin notice '{notice_id}' not found in settlement")
        if self._state.bulletin_notices[notice_id].status == "removed":
            raise ValueError(f"Bulletin notice '{notice_id}' is already removed")

        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            BulletinNoticeRemovedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=notice_id,
            settlement_id=sid,
            remover_id=str(remover_id),
            reason=reason,
            metadata=metadata or {},
        )
        return notice_id

    def decrypt_cipher_notice(
        self,
        notice_id: str,
        player_id: str,
        solution: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Decrypt a cipher-encoded notice when a player submits the correct solution."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")
        if notice_id not in self._state.bulletin_notices:
            raise ValueError(f"Bulletin notice '{notice_id}' not found in settlement")

        notice = self._state.bulletin_notices[notice_id]
        if not notice.cipher_encoded:
            return notice.content

        expected = notice.cipher_solution.strip().lower()
        submitted = solution.strip().lower()
        if expected and submitted != expected:
            raise ValueError("Incorrect cipher solution")

        sid = str(self._state.settlement_id or self.aggregate_id)
        self.create_event(
            CipherNoticeDecryptedEvent,
            aggregate_id=_to_uuid(sid),
            notice_id=notice_id,
            settlement_id=sid,
            player_id=str(player_id),
            decrypted_content=notice.hidden_content or notice.content,
            metadata=metadata or {},
        )
        return notice.hidden_content or notice.content
