"""Aggregator facade re-exporting settlement auth and permissions for backward compatibility."""

from __future__ import annotations

import game_session.settlement.auth as _pkg

for _name in _pkg.__all__:
    globals()[_name] = getattr(_pkg, _name)

__all__ = list(_pkg.__all__)
