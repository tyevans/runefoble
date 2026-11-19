"""Shared kernel of the game session service (ADR-0021 D1, D2).

This package holds route identity, permission helpers that two or more domain
packages call, the child index mechanism, and the stream names. It imports no
domain package of `game_session` (ADR-0021 D4 rule 5).
"""
