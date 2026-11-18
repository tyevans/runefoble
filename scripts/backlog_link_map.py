"""Reviewed retargets for dead links in refined and proposed backlog tasks (TASK-0666).

Each key is (task id, cited file name). The value is the replacement file name in the
same registry folder, or None when no governing record exists and the link is removed
(the link text stays, the target goes). Every decision was made by reading the task title
and the target title. Do not add a guess here: add a row only after reading both titles.
"""

from __future__ import annotations

LINK_MAP: dict[tuple[str, str], str | None] = {
    # refined
    ("0434", "us-0001-developer-local-environment-setup.md"): None,
    (
        "0434",
        "us-0065-game-session-staging-lobby-and-pre-game-assembly.md",
    ): "us-0065-game-session-lobby-readiness-and-launch.md",
    (
        "0437",
        "us-0065-game-session-staging-lobby-and-pre-game-assembly.md",
    ): "us-0039-encounter-tension-adaptive-scoring-and-foley.md",
    (
        "0438",
        "us-0048-kinetic-spell-vfx-and-particle-bloom.md",
    ): "us-0048-kinetic-spell-vfx-and-particle-canvas.md",
    (
        "0438",
        "us-0061-tabletop-3d-physics-and-dice-collisions.md",
    ): "us-0061-3d-miniature-tokens-and-tabletop-physics.md",
    (
        "0440",
        "us-0065-game-session-staging-lobby-and-pre-game-assembly.md",
    ): "us-0031-live-stream-audience-chaos-polls-and-rumors.md",
    (
        "0444",
        "us-0064-character-roster-and-party-assignment.md",
    ): "us-0064-character-roster-management-and-party-assignment.md",
    (
        "0445",
        "us-0069-deep-linkable-client-routing-and-route-guards.md",
    ): "us-0055-dynamic-character-wardrobe-and-condition-portraits.md",
    (
        "0446",
        "us-0039-adaptive-tension-and-combat-audio-scoring.md",
    ): "us-0046-character-musical-leitmotifs-and-dynamic-themes.md",
    ("0485", "prd-0001-runefoble-platform-foundations.md"): None,
    ("0485", "us-0010-developer-local-infrastructure-and-test-tooling.md"): None,
    ("0486", "prd-0001-runefoble-platform-foundations.md"): None,
    ("0486", "us-0010-developer-local-infrastructure-and-test-tooling.md"): None,
    (
        "0490",
        "prd-0003-the-watcher-autonomous-dm-engine.md",
    ): "prd-0001-the-watcher-ai-dm-and-board-animator.md",
    (
        "0490",
        "us-0002-autonomous-dm-intent-arbitration.md",
    ): "us-0007-autonomous-dm-session-execution.md",
    (
        "0490",
        "us-0003-missing-player-tactical-stand-in.md",
    ): "us-0025-personalized-ai-stand-in-tactical-policies.md",
    ("0491", "prd-0004-realtime-game-session-orchestration.md"): None,
    (
        "0491",
        "prd-0012-frontier-settlements-and-havens.md",
    ): "prd-0024-settlement-haven-builder-and-mobile-minigames.md",
    (
        "0491",
        "us-0004-session-lobby-and-player-readiness.md",
    ): "us-0065-game-session-lobby-readiness-and-launch.md",
    (
        "0491",
        "us-0044-charter-frontier-settlement-haven.md",
    ): "us-0072-mobile-responsive-settlement-browser-and-town-builder.md",
    (
        "0492",
        "prd-0005-tactile-board-state-and-fog-of-war.md",
    ): "prd-0003-spatial-fog-of-war-and-visibility-engine.md",
    (
        "0492",
        "us-0005-tactile-token-movement-and-snapping.md",
    ): "us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md",
    (
        "0492",
        "us-0027-spoken-ghost-token-movement-previews.md",
    ): "us-0022-tactical-ghost-path-and-dynamic-cover-arcs.md",
    (
        "0493",
        "prd-0006-character-sheet-and-inventory.md",
    ): "prd-0006-digital-character-sheet-inventory-and-conditions.md",
    (
        "0493",
        "prd-0009-campfire-crafting-and-resting-boons.md",
    ): "prd-0014-downtime-crafting-and-stronghold-engine.md",
    (
        "0493",
        "us-0006-character-sheet-equipment-inventory.md",
    ): "us-0015-character-inventory-equipment-tracking.md",
    (
        "0493",
        "us-0018-character-progression-and-spellbook.md",
    ): "us-0051-character-level-progression-and-spellbook.md",
    (
        "0494",
        "prd-0007-realtime-voice-streaming-and-dsp.md",
    ): "prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md",
    (
        "0494",
        "us-0007-voice-streaming-audio-pipeline.md",
    ): "us-0001-player-commands-board-via-voice.md",
    (
        "0494",
        "us-0020-voice-dsp-conditioning-filters.md",
    ): "us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md",
    (
        "0499",
        "prd-0011-live-audience-chaos-studio-and-spectator-overlay.md",
    ): "prd-0011-live-spectator-studio-and-audience-interactivity.md",
    (
        "0499",
        "us-0014-real-time-spectator-clean-overlay.md",
    ): "us-0006-realtime-spectator-stream-and-chronicle.md",
    (
        "0499",
        "us-0043-audience-chaos-polls-and-voting.md",
    ): "us-0031-live-stream-audience-chaos-polls-and-rumors.md",
    (
        "0502",
        "prd-0001-runefoble-platform-foundations.md",
    ): "prd-0023-unified-frontend-application-shell-and-campaign-hub.md",
    ("0502", "us-0010-developer-local-infrastructure-and-test-tooling.md"): None,
    (
        "0502",
        "us-0065-routed-app-shell-views-and-session-transitions.md",
    ): "us-0066-client-side-routing-navigation-and-breadcrumbs.md",
    # proposed
    (
        "0435",
        "us-0015-dynamic-equipment-slots-and-encumbrance.md",
    ): "us-0015-character-inventory-equipment-tracking.md",
    (
        "0435",
        "us-0051-character-sheet-inventory-equipment-and-conditions.md",
    ): "us-0055-dynamic-character-wardrobe-and-condition-portraits.md",
    ("0442", "us-0001-developer-local-environment-setup.md"): None,
    (
        "0442",
        "us-0065-game-session-staging-lobby-and-pre-game-assembly.md",
    ): "us-0065-game-session-lobby-readiness-and-launch.md",
    (
        "0443",
        "us-0015-dynamic-equipment-slots-and-encumbrance.md",
    ): "us-0015-character-inventory-equipment-tracking.md",
    (
        "0443",
        "us-0051-character-sheet-inventory-equipment-and-conditions.md",
    ): "us-0055-dynamic-character-wardrobe-and-condition-portraits.md",
    (
        "0443",
        "us-0069-deep-linkable-client-routing-and-route-guards.md",
    ): "us-0069-character-sheet-inspector-and-active-session-binding.md",
    (
        "0447",
        "us-0015-dynamic-equipment-slots-and-encumbrance.md",
    ): "us-0015-character-inventory-equipment-tracking.md",
    (
        "0447",
        "us-0051-character-sheet-inventory-equipment-and-conditions.md",
    ): "us-0055-dynamic-character-wardrobe-and-condition-portraits.md",
    (
        "0447",
        "us-0064-character-roster-and-party-assignment.md",
    ): "us-0064-character-roster-management-and-party-assignment.md",
    (
        "0447",
        "us-0069-deep-linkable-character-sheet-route.md",
    ): "us-0069-character-sheet-inspector-and-active-session-binding.md",
    (
        "0452",
        "us-0067-campaign-detail-view-orchestration.md",
    ): "us-0050-collaborative-campaign-atlas-and-living-codex.md",
    (
        "0453",
        "us-0067-campaign-detail-view-orchestration.md",
    ): "us-0058-west-marches-shared-world-state-and-caravan-trade.md",
    (
        "0459",
        "us-0045-generative-handouts-wax-seals-and-3d-relics.md",
    ): "us-0045-generative-in-world-handouts-and-relic-inspector.md",
    (
        "0461",
        "us-0004-missing-player-ai-stand-in.md",
    ): "us-0005-absentee-session-chronicle-recap.md",
    (
        "0473",
        "us-0067-campaign-detail-dashboard-and-tabbed-navigation.md",
    ): "us-0067-campaign-detail-view-and-session-scheduling.md",
    (
        "0484",
        "us-0068-user-profile-and-account-settings.md",
    ): "us-0070-user-account-settings-and-profile-management.md",
    (
        "0507",
        "us-0014-tactile-board-fog-of-war.md",
    ): "us-0012-spatial-line-of-sight-and-fog-of-war.md",
    (
        "0512",
        "us-0064-character-roster-and-party-assignment.md",
    ): "us-0064-character-roster-management-and-party-assignment.md",
}

# Frontmatter reference corrections: (task id, old id) -> new id.
REFERENCE_MAP: dict[tuple[str, str], str] = {
    ("0367", "PRD-0025"): "PRD-0024",
}

# Cited-path decisions that override the unique-name search (TASK-0666).
# (task id, cited path) -> new path, or None to mark the path `(removed)`.
# Name-only matches that describe a different module are rejected here.
PATH_OVERRIDES: dict[tuple[str, str], str | None] = {
    ("0083", "tests/fixtures/audio.py"): None,
    ("0197", "services/asset_forge/src/asset_forge/generator.py"): None,
    ("0497", "services/asset_forge/src/asset_forge/generator.py"): None,
}
