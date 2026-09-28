"""Aggregator facade re-exporting character sheet models for backward compatibility."""

from __future__ import annotations

import character_sheet.models as _pkg

for _name in _pkg.__all__:
    globals()[_name] = getattr(_pkg, _name)

__all__ = list(_pkg.__all__)
