"""Spell bloom impact: cells, tokens and ephemeral decal for a spell radius."""

from __future__ import annotations

from typing import Any

from board_state.geometry import cells_as_set, cells_in_shape


def compute_spell_vfx_impact(
    target_x: int,
    target_y: int,
    cols: int,
    rows: int,
    tokens: dict[str, Any],
    radius_ft: int,
    spell_name: str,
    spell_archetype: str,
    damage_type: str | None,
) -> tuple[list[list[int]], list[str], str | None]:
    """Compute cells and tokens enclosed in spell radius bloom, plus ephemeral decal type.

    The bloom is a sphere placed on the target cell. It uses the same containment rule as
    the AoE template evaluation (board_state.geometry).
    """
    affected_cells: list[list[int]] = []
    affected_token_ids: list[str] = []
    decal_type: str | None = None

    if radius_ft > 0:
        affected_cells = cells_in_shape(
            cols, rows, "sphere", target_x, target_y, radius_ft=float(radius_ft)
        )
        affected_cell_set = cells_as_set(affected_cells)

        for tok_id, tok in tokens.items():
            if (tok.x, tok.y) in affected_cell_set:
                affected_token_ids.append(tok_id)

        sp_lower = spell_name.lower()
        dt_lower = (damage_type or "").lower()
        if spell_archetype == "evocation":
            if "lightning" in sp_lower or "lightning" in dt_lower:
                decal_type = "lightning_scorch"
            elif "cold" in sp_lower or "frost" in sp_lower or "cold" in dt_lower:
                decal_type = "frost"
            else:
                decal_type = "scorched_earth"
        elif spell_archetype == "conjuration":
            decal_type = "portal_residue"
        elif spell_archetype == "abjuration":
            decal_type = "abjuration_glyph"

    return affected_cells, affected_token_ids, decal_type
