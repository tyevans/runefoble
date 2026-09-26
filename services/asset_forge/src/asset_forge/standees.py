"""Papercraft standee generator for folding tabletop paper miniatures.

Generates print-ready sheets with mirrored front/back artwork, nameplates,
cut guides, and foldable base tabs calibrated to standard miniature sizes.
"""

from __future__ import annotations

from typing import Any

from asset_forge.pdf_tiler import PAGE_SIZES, _build_pdf_stream


def generate_standees_pdf(
    standees: list[dict[str, Any]],
    page_size: str = "letter",
    sheet_title: str = "Runefoble Tabletop Standees",
) -> tuple[bytes, dict[str, Any]]:
    """Generate print-ready PDF containing folding papercraft miniature standees."""
    pw, ph = PAGE_SIZES.get(page_size.lower(), PAGE_SIZES["letter"])
    margin = 36.0  # 0.5 inch margins
    std_w = 80.0  # Width of each standee (~1.1 inch)
    std_h = 100.0  # Face height (front and back face each)
    tab_h = 28.0  # Base tab height (~0.4 inch)
    total_std_h = (std_h * 2) + (tab_h * 2)  # Full unfolded standee strip height

    usable_w = pw - (2 * margin)
    cols = max(1, int(usable_w // (std_w + 14.0)))

    pages: list[tuple[float, float, str]] = []
    standee_chunks = [
        standees[i : i + (cols * 2)] for i in range(0, max(1, len(standees)), cols * 2)
    ]

    for chunk in standee_chunks:
        cmds = ["q", "0.5 w"]
        # Header banner and instructions
        banner_y = ph - margin - 12.0
        cmds.append(
            f"BT /F1 10 Tf 0 0 0 rg {margin:.2f} {banner_y:.2f} Td "
            f"({sheet_title} | Cut along solid border, fold at dashed apex) Tj ET"
        )

        for idx, item in enumerate(chunk):
            col_idx = idx % cols
            row_idx = idx // cols
            sx = margin + col_idx * (std_w + 14.0)
            sy = ph - margin - 32.0 - ((row_idx + 1) * (total_std_h + 10.0))
            if sy < margin:
                continue

            name = str(item.get("name", f"Standee #{idx + 1}"))[:16]
            stype = str(item.get("type", "pc")).upper()
            hp = item.get("hp", 10)

            # Outer solid cut line

            cmds.append(f"0 0 0 RG 0.75 w {sx:.2f} {sy:.2f} {std_w:.2f} {total_std_h:.2f} re S")

            # 1. Bottom Base Tab
            tab1_y = sy
            cmds.append(f"0.9 0.9 0.9 rg {sx:.2f} {tab1_y:.2f} {std_w:.2f} {tab_h:.2f} re f")
            cmds.append(
                f"BT /F1 7 Tf 0.3 0.3 0.3 rg {sx + 8:.2f} {tab1_y + 10:.2f} Td (FOLD BASE TAB) Tj ET"
            )
            cmds.append(
                f"[3 3] 0 d 0.5 w {sx:.2f} {tab1_y + tab_h:.2f} m {sx + std_w:.2f} {tab1_y + tab_h:.2f} l S [] 0 d"
            )

            # 2. Front Face
            front_y = tab1_y + tab_h
            cmds.append(f"0.96 0.96 0.96 rg {sx:.2f} {front_y:.2f} {std_w:.2f} {std_h:.2f} re f")
            # Portrait frame
            cmds.append(
                f"0.8 0.8 0.8 rg {sx + 8:.2f} {front_y + 30:.2f} {std_w - 16:.2f} {std_h - 38:.2f} re f"
            )
            cmds.append(
                f"BT /F1 8 Tf 0.2 0.2 0.2 rg {sx + 12:.2f} {front_y + 55:.2f} Td ([{stype}]) Tj ET"
            )
            # Front Nameplate
            cmds.append(f"0.15 0.15 0.18 rg {sx + 4:.2f} {front_y + 6:.2f} {std_w - 8:.2f} 18 re f")
            cmds.append(f"BT /F1 8 Tf 1 1 1 rg {sx + 8:.2f} {front_y + 11:.2f} Td ({name}) Tj ET")
            cmds.append(
                f"BT /F1 7 Tf 0.9 0.3 0.3 rg {sx + std_w - 24:.2f} {front_y + 11:.2f} Td (HP {hp}) Tj ET"
            )

            # Center fold line (dashed)
            apex_y = front_y + std_h
            cmds.append(
                f"[4 4] 0 d 1 w 0.2 0.2 0.2 RG {sx:.2f} {apex_y:.2f} m {sx + std_w:.2f} {apex_y:.2f} l S [] 0 d"
            )

            # 3. Back Face (Mirrored inverted face)
            back_y = apex_y
            cmds.append(f"0.92 0.92 0.92 rg {sx:.2f} {back_y:.2f} {std_w:.2f} {std_h:.2f} re f")
            cmds.append(
                f"0.85 0.85 0.85 rg {sx + 8:.2f} {back_y + 8:.2f} {std_w - 16:.2f} {std_h - 38:.2f} re f"
            )
            # Mirrored back label
            cmds.append(
                f"0.25 0.25 0.28 rg {sx + 4:.2f} {back_y + std_h - 24:.2f} {std_w - 8:.2f} 18 re f"
            )
            cmds.append(
                f"BT /F1 8 Tf 1 1 1 rg {sx + 8:.2f} {back_y + std_h - 18:.2f} Td ({name} - BACK) Tj ET"
            )

            # 4. Top Base Tab
            tab2_y = back_y + std_h
            cmds.append(
                f"[3 3] 0 d 0.5 w {sx:.2f} {tab2_y:.2f} m {sx + std_w:.2f} {tab2_y:.2f} l S [] 0 d"
            )
            cmds.append(f"0.9 0.9 0.9 rg {sx:.2f} {tab2_y:.2f} {std_w:.2f} {tab_h:.2f} re f")
            cmds.append(
                f"BT /F1 7 Tf 0.3 0.3 0.3 rg {sx + 8:.2f} {tab2_y + 10:.2f} Td (FOLD BASE TAB) Tj ET"
            )

        cmds.append("Q")
        pages.append((pw, ph, "\n".join(cmds)))

    pdf_bytes = _build_pdf_stream(pages)
    meta = {
        "standee_count": len(standees),
        "pages": len(pages),
        "page_size": page_size,
        "format": "folding_papercraft",
    }
    return pdf_bytes, meta
