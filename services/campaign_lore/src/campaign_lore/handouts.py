"""Generative diegetic handout engine, wax seal physics, and 3D relic synthesizer."""

import math
from typing import Any
from uuid import uuid4

# Wax seal stamp symbols with SVG path representations
SEAL_STAMPS: dict[str, dict[str, Any]] = {
    "raven_crest": {
        "name": "Raven Crest",
        "description": "Heraldic raven perched atop a cracked skull",
        "svg_path": "M 50 20 C 40 25 35 35 38 48 C 30 50 25 60 28 72 C 35 68 42 67 48 70 C 45 78 52 82 58 79 C 62 68 65 52 62 38 C 60 28 55 22 50 20 Z",
    },
    "dragon_eye": {
        "name": "Dragon Eye",
        "description": "Slitted reptilian pupil encircled by arcane runes",
        "svg_path": "M 20 50 Q 50 20 80 50 Q 50 80 20 50 Z M 48 30 Q 52 40 52 50 Q 52 60 48 70 Q 44 60 44 50 Q 44 40 48 30 Z",
    },
    "sunburst": {
        "name": "Solar Dawn",
        "description": "Radiant multi-pointed sunburst symbol of Neverwinter",
        "svg_path": "M 50 30 L 54 44 L 68 44 L 57 52 L 61 66 L 50 58 L 39 66 L 43 52 L 32 44 L 46 44 Z",
    },
    "arcane_eye": {
        "name": "Watcher's Eye",
        "description": "All-seeing mystic eye with concentric runic iris",
        "svg_path": "M 15 50 Q 50 15 85 50 Q 50 85 15 50 Z M 50 35 A 15 15 0 1 0 50 65 A 15 15 0 1 0 50 35 Z",
    },
}

SEAL_COLORS: dict[str, dict[str, str]] = {
    "crimson": {"primary": "#8b0000", "highlight": "#b22222", "shadow": "#4a0000"},
    "imperial_gold": {"primary": "#b8860b", "highlight": "#ffd700", "shadow": "#5c4308"},
    "midnight_blue": {"primary": "#191970", "highlight": "#4169e1", "shadow": "#0d0d3a"},
    "emerald": {"primary": "#006400", "highlight": "#2e8b57", "shadow": "#003300"},
    "obsidian": {"primary": "#1a1a1a", "highlight": "#333333", "shadow": "#0a0a0a"},
}

PAPER_TEXTURES: dict[str, dict[str, Any]] = {
    "weathered_parchment": {
        "background": "#f4ecd8",
        "border_color": "#8c6b45",
        "roughness": 0.75,
        "burnt_edges": True,
        "stains_count": 3,
    },
    "royal_vellum": {
        "background": "#faf6ee",
        "border_color": "#d4af37",
        "roughness": 0.2,
        "burnt_edges": False,
        "stains_count": 0,
    },
    "ancient_papyrus": {
        "background": "#e2caa3",
        "border_color": "#634832",
        "roughness": 0.9,
        "burnt_edges": True,
        "stains_count": 5,
    },
}

CALLIGRAPHY_FONTS: dict[str, dict[str, str]] = {
    "royal_chancery": {"font_family": "serif", "letter_spacing": "0.04em", "line_height": "1.7"},
    "elvish_script": {"font_family": "cursive", "letter_spacing": "0.08em", "line_height": "1.9"},
    "dwarven_runic": {"font_family": "monospace", "letter_spacing": "0.12em", "line_height": "1.5"},
    "cursed_blackletter": {
        "font_family": "fantasy",
        "letter_spacing": "0.05em",
        "line_height": "1.6",
    },
}


class HandoutSynthesizer:
    """Synthesizes diegetic handouts with parchment styles, wax seals, and invisible ink."""

    @classmethod
    def generate_handout_spec(
        cls,
        title: str,
        content: str,
        handout_type: str = "letter",
        paper_texture: str = "weathered_parchment",
        calligraphy_font: str = "royal_chancery",
        seal_color: str = "crimson",
        seal_stamp: str = "raven_crest",
        secret_ink_text: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured visual and physical specifications for a diegetic handout."""
        paper = PAPER_TEXTURES.get(paper_texture, PAPER_TEXTURES["weathered_parchment"])
        font = CALLIGRAPHY_FONTS.get(calligraphy_font, CALLIGRAPHY_FONTS["royal_chancery"])
        stamp = SEAL_STAMPS.get(seal_stamp, SEAL_STAMPS["raven_crest"])
        palette = SEAL_COLORS.get(seal_color, SEAL_COLORS["crimson"])

        wax_seal = {
            "state": "intact",
            "color": seal_color,
            "palette": palette,
            "stamp_symbol": seal_stamp,
            "stamp_name": stamp["name"],
            "svg_stamp_path": stamp["svg_path"],
            "physics": {
                "stiffness": 0.85,
                "brittleness": 0.95,
                "break_threshold_n": 12.5,
                "crack_paths": [
                    "M 50 10 L 48 35 L 53 50 L 49 70 L 52 90",
                    "M 48 35 L 30 40 L 15 36",
                    "M 53 50 L 70 54 L 86 52",
                ],
            },
            "audio_profiles": {
                "crack": "wax_crack_crisp_01.wav",
                "fracture_heavy": "wax_fracture_heavy.wav",
            },
        }

        invisible_ink = None
        has_ink = secret_ink_text is not None and len(secret_ink_text.strip()) > 0
        if has_ink:
            invisible_ink = {
                "secret_text": secret_ink_text,
                "revealed": False,
                "wavelength_nm": 365,
                "activation_radius_px": 110,
                "luminescence_color": "#00ffcc",
                "glow_blur_px": 6,
            }

        return {
            "title": title,
            "handout_type": handout_type,
            "paper_texture": paper_texture,
            "paper_spec": paper,
            "calligraphy_font": calligraphy_font,
            "calligraphy_spec": font,
            "content": content,
            "has_wax_seal": True,
            "wax_seal": wax_seal,
            "has_invisible_ink": has_ink,
            "invisible_ink": invisible_ink,
        }


class RelicSynthesizer:
    """Synthesizes WebGL 3D model geometry descriptors, PBR shaders, and interactive rune hitboxes."""

    RELIC_PRESETS: dict[str, dict[str, Any]] = {
        "amulet_sunken_spire": {
            "name": "Amulet of the Sunken Spire",
            "relic_type": "amulet",
            "model_geometry": "amulet_sunken_spire",
            "shader_properties": {
                "metallic": 0.88,
                "roughness": 0.22,
                "base_color": "#2c3e50",
                "emissive_color": "#00ffcc",
                "emissive_intensity": 1.4,
                "pulsation_speed": 1.2,
            },
            "runes": [
                {
                    "id": "rune-spire-1",
                    "inscription": "Khar-Drak-Mor",
                    "position": [0.0, 0.35, -0.15],
                    "hitbox_radius": 0.12,
                    "translated": "By Blood Sealed",
                    "secret": False,
                },
                {
                    "id": "rune-spire-2",
                    "inscription": "Val-Teth-Azul",
                    "position": [-0.25, -0.1, -0.12],
                    "hitbox_radius": 0.1,
                    "translated": "The Spire Slumbers Beneath Deep Waters",
                    "secret": False,
                },
            ],
        },
        "dagger_shadow_weave": {
            "name": "Dagger of the Shadow Weave",
            "relic_type": "dagger",
            "model_geometry": "dagger_shadow_weave",
            "shader_properties": {
                "metallic": 0.95,
                "roughness": 0.15,
                "base_color": "#121218",
                "emissive_color": "#a855f7",
                "emissive_intensity": 1.8,
                "pulsation_speed": 0.8,
            },
            "runes": [
                {
                    "id": "rune-dagger-1",
                    "inscription": "Nox-Siphon",
                    "position": [0.0, 0.5, 0.05],
                    "hitbox_radius": 0.08,
                    "translated": "Drink the Unseen Light",
                    "secret": False,
                }
            ],
        },
        "puzzle_box_celestial": {
            "name": "Celestial Chrono-Sphere",
            "relic_type": "puzzle_box",
            "model_geometry": "puzzle_box_celestial",
            "shader_properties": {
                "metallic": 0.72,
                "roughness": 0.32,
                "base_color": "#d4af37",
                "emissive_color": "#f59e0b",
                "emissive_intensity": 1.0,
                "pulsation_speed": 1.5,
            },
            "runes": [
                {
                    "id": "rune-box-1",
                    "inscription": "Aethel-Sol-Lux",
                    "position": [0.3, 0.0, 0.3],
                    "hitbox_radius": 0.15,
                    "translated": "Turn Three Rings When the Moon Weeps",
                    "secret": False,
                }
            ],
        },
    }

    @classmethod
    def generate_relic_spec(
        cls,
        name: str,
        relic_type: str = "amulet",
        model_geometry: str = "amulet_sunken_spire",
        custom_runes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Produce complete 3D WebGL mesh descriptor and rune coordinates."""
        preset = cls.RELIC_PRESETS.get(model_geometry, cls.RELIC_PRESETS["amulet_sunken_spire"])

        runes = custom_runes if custom_runes is not None else list(preset["runes"])
        for rune in runes:
            if "id" not in rune:
                rune["id"] = f"rune-{uuid4().hex[:6]}"

        # Procedural WebGL vertex buffer generator for standalone 3D rendering
        mesh_data = cls._generate_procedural_mesh(model_geometry)

        return {
            "name": name or preset["name"],
            "relic_type": relic_type,
            "model_geometry": model_geometry,
            "shader_properties": dict(preset["shader_properties"]),
            "runes": runes,
            "mesh_data": mesh_data,
        }

    @classmethod
    def _generate_procedural_mesh(cls, geometry_type: str) -> dict[str, Any]:
        """Generate procedural 3D polygon vertices and normals for WebGL canvas."""
        vertices: list[float] = []
        indices: list[int] = []
        normals: list[float] = []

        # Simple parametric 8-sided ring/disc geometry for WebGL orbit view
        segments = 16
        radius = 1.0
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            vertices.extend([round(x, 4), round(y, 4), 0.0])
            normals.extend([0.0, 0.0, 1.0])

        for i in range(1, segments - 1):
            indices.extend([0, i, i + 1])

        return {
            "vertex_count": len(vertices) // 3,
            "index_count": len(indices),
            "vertices": vertices,
            "indices": indices,
            "normals": normals,
            "primitive_type": "TRIANGLES",
        }
