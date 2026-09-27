"""DM Intelligence Bulletin and Geopolitical Shift narrative formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from the_watcher.faction_models import FactionResponse, GeopoliticalShiftModel
    from the_watcher.factions import FactionAggregate


def generate_geopolitical_shift(
    faction: FactionAggregate, territory: str
) -> tuple[str, str, str, list[str]]:
    """Determine shift type, narrative summary, severity, and ripples for an agenda."""
    state = faction.state
    name = state.name
    goal = state.active_goal.lower()

    if "smuggle" in goal or "weapons" in goal or "trade" in goal:
        shift_type = "trade_shortage"
        desc = (
            f"{name} flooded {territory} with black-market contraband, triggering trade shortages."
        )
        effects = [
            "Merchant weapons markup increased by 25%",
            "City watch checkpoints double inspections",
            "Tavern whispers warning of covert arsenals",
        ]
    elif "outpost" in goal or "seize" in goal or "patrol" in goal:
        shift_type = "territory_captured"
        desc = f"{name} established fortified control over the {territory} perimeter."
        effects = [
            f"{name} patrols garrison the road",
            "Travel permits enforced for merchant carts",
        ]
    else:
        shift_type = "martial_law"
        desc = f"{name}'s subversive activities forced heightened security in {territory}."
        effects = [
            "Nightly curfews enforced by town bailiffs",
            "Disreputable contacts operating in deep shadows",
        ]
    severity = "critical" if state.influence > 60 else "moderate"
    return shift_type, desc, severity, effects


def build_intelligence_bulletin(
    campaign_id: str,
    tick: int,
    stability: int,
    factions: list[FactionResponse],
    shifts: list[GeopoliticalShiftModel],
    rumors: list[str],
) -> str:
    """Format structured markdown intelligence brief for the Dungeon Master."""
    lines = [
        f"# 📜 THE WATCHER INTELLIGENCE BULLETIN: WORLD TICK #{tick}",
        f"**Campaign**: `{campaign_id}` | **Regional Stability**: {stability}/100",
        "",
        "## ⚔️ Geopolitical & Territorial Shifts",
    ]
    if shifts:
        for s in shifts:
            lines.append(f"- **[{s.territory}] {s.shift_type.upper()}**: {s.description}")
    else:
        lines.append("- *No major territorial transfers occurred during this cycle.*")

    lines.extend(["", "## 🏛️ Faction Agenda Progress"])
    for f in factions:
        lines.append(f"- **{f.name}** (Influence: {f.influence}, Resources: {f.resources})")
        lines.append(f"  - *Active Agenda*: {f.active_goal}")
        lines.append(f"  - *Progress*: {f.goal_progress}/{f.goal_target}%")

    lines.extend(["", "## 🍻 Evolving Tavern Rumors (Player Feed Hooks)"])
    for r in rumors:
        lines.append(f'- *"{r}"*')

    lines.extend(
        [
            "",
            "## 👁️ The Watcher's Tactical Advisory",
            "- **Board State Ripple**: Update token presence and sentry crests in affected sectors.",
            "- **Merchant Cues**: Adjust goods availability and markups based on regional trade flow.",
            "- **NPC Dialogue**: Spoken interactions should mirror current tavern gossip and suspicion.",
        ]
    )
    return "\n".join(lines)
