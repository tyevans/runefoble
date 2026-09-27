"""Condition and Injury Overlay Engine for Character Portraits.

Dynamic SVG composition applying bloodied vignettes (<50% HP), poisoned auras,
and stunned dizzy status overlays over base character portraits and tokens.
"""

from __future__ import annotations

import urllib.parse
from typing import Any


def compute_condition_badges(
    current_hp: int,
    max_hp: int,
    conditions: dict[str, Any] | list[str] | None = None,
) -> list[str]:
    """Compute active status badges based on HP thresholds and condition afflictions."""
    badges: list[str] = []

    # Bloodied threshold: current HP strictly below 50% of maximum HP
    if max_hp > 0 and current_hp < (max_hp * 0.5):
        badges.append("bloodied")

    if current_hp <= 0:
        badges.append("downed")

    if conditions:
        cond_keys = (
            list(conditions.keys())
            if isinstance(conditions, dict)
            else [str(c) for c in conditions]
        )
        for cond in cond_keys:
            c_lower = cond.lower().strip()
            if c_lower and c_lower not in badges:
                badges.append(c_lower)

    return badges


def compose_portrait_svg(
    base_url: str,
    current_hp: int,
    max_hp: int,
    conditions: dict[str, Any] | list[str] | None = None,
    width: int = 256,
    height: int = 256,
) -> str:
    """Compose dynamic SVG markup with bloodied vignettes, poisoned auras, and dizzy stars."""
    badges = compute_condition_badges(current_hp, max_hp, conditions)
    is_bloodied = "bloodied" in badges
    is_poisoned = "poisoned" in badges
    is_stunned = "stunned" in badges

    # Clean XML attributes
    safe_base_url = (base_url or "/assets/portraits/default.svg").replace('"', "&quot;")

    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" class="runefoble-portrait-svg">',
        "  <defs>",
        '    <clipPath id="rf-portrait-clip">',
        f'      <circle cx="{width / 2}" cy="{height / 2}" r="{(width / 2) - 8}" />',
        "    </clipPath>",
        '    <radialGradient id="bloodied-vignette" cx="50%" cy="50%" r="50%">',
        '      <stop offset="35%" stop-color="#700000" stop-opacity="0" />',
        '      <stop offset="75%" stop-color="#b30000" stop-opacity="0.55" />',
        '      <stop offset="100%" stop-color="#4a0000" stop-opacity="0.85" />',
        "    </radialGradient>",
        '    <radialGradient id="poisoned-aura" cx="50%" cy="50%" r="50%">',
        '      <stop offset="50%" stop-color="#00ff66" stop-opacity="0" />',
        '      <stop offset="85%" stop-color="#2ec4b6" stop-opacity="0.45" />',
        '      <stop offset="100%" stop-color="#0e402d" stop-opacity="0.8" />',
        "    </radialGradient>",
        '    <filter id="stunned-glow">',
        '      <feGaussianBlur stdDeviation="2.5" result="glow" />',
        "      <feMerge>",
        '        <feMergeNode in="glow" />',
        '        <feMergeNode in="SourceGraphic" />',
        "      </feMerge>",
        "    </filter>",
        "  </defs>",
        '  <g clip-path="url(#rf-portrait-clip)">',
        f'    <rect width="{width}" height="{height}" fill="#1e1e24" />',
        f'    <image href="{safe_base_url}" width="{width}" height="{height}" '
        'preserveAspectRatio="xMidYMid slice" />',
    ]

    # Bloodied Vignette and Red Scratch Decals
    if is_bloodied:
        svg_parts.extend(
            [
                f'    <rect width="{width}" height="{height}" fill="url(#bloodied-vignette)" '
                'class="bloodied-vignette" />',
                f'    <circle cx="{width / 2}" cy="{height / 2}" r="{(width / 2) - 8}" '
                'stroke="#e63946" stroke-width="6" fill="none" class="bloodied-border" />',
                '    <path d="M 45,70 Q 60,95 75,90 M 65,60 Q 80,90 90,120 M 175,55 Q 195,80 185,115" '
                'stroke="#ef233c" stroke-width="3.5" stroke-linecap="round" fill="none" '
                'opacity="0.85" class="blood-scratches" />',
            ]
        )

    # Poisoned Aura and Miasma Particles
    if is_poisoned:
        svg_parts.extend(
            [
                f'    <rect width="{width}" height="{height}" fill="url(#poisoned-aura)" '
                'class="poisoned-aura" />',
                f'    <circle cx="{width / 2}" cy="{height / 2}" r="{(width / 2) - 12}" '
                'stroke="#00f5d4" stroke-width="4" stroke-dasharray="10 6" fill="none" '
                'class="poisoned-ring" />',
                '    <g class="poison-bubbles" fill="#00f5d4" opacity="0.8">',
                '      <circle cx="75" cy="180" r="5" />',
                '      <circle cx="95" cy="195" r="3.5" />',
                '      <circle cx="165" cy="185" r="4.5" />',
                '      <circle cx="185" cy="205" r="6" />',
                "    </g>",
            ]
        )

    # Stunned Dizzy Halo & Stars
    if is_stunned:
        svg_parts.extend(
            [
                '    <g class="stunned-stars" filter="url(#stunned-glow)" fill="#ffd166">',
                '      <polygon points="128,26 131,35 140,35 133,40 135,49 128,44 121,49 123,40 116,35 125,35" />',
                '      <polygon points="86,42 88,48 95,48 90,52 92,58 86,54 81,58 83,52 77,48 84,48" />',
                '      <polygon points="170,42 172,48 179,48 174,52 176,58 170,54 165,58 167,52 161,48 168,48" />',
                "    </g>",
            ]
        )

    svg_parts.extend(
        [
            "  </g>",
            f'  <circle cx="{width / 2}" cy="{height / 2}" r="{(width / 2) - 6}" '
            f'stroke="{("#e63946" if is_bloodied else ("#00f5d4" if is_poisoned else "#3a3d40"))}" '
            'stroke-width="3" fill="none" />',
            "</svg>",
        ]
    )

    return "\n".join(svg_parts)


def svg_to_data_url(svg_content: str) -> str:
    """Encode SVG string into standard data:image/svg+xml data URL."""
    clean_svg = " ".join(svg_content.split())
    encoded = urllib.parse.quote(clean_svg)
    return f"data:image/svg+xml;utf8,{encoded}"


def resolve_active_portrait_url(
    base_url: str,
    current_hp: int,
    max_hp: int,
    conditions: dict[str, Any] | list[str] | None = None,
) -> str:
    """Resolve active portrait URL, applying SVG condition overlays when injured or afflicted."""
    badges = compute_condition_badges(current_hp, max_hp, conditions)

    # If healthy with no active visual overlays, preserve pure base URL
    if not any(b in badges for b in ("bloodied", "downed", "poisoned", "stunned")):
        return base_url or "/assets/portraits/default.svg"

    # Otherwise synthesize composited SVG data URL
    svg = compose_portrait_svg(base_url, current_hp, max_hp, conditions)
    return svg_to_data_url(svg)
