"""Session authorization policies shared by Game Session routers (ADR-0001, ADR-0015).

Permissions come from the SpiceDB schema only. No role name or token claim grants access.
"""

from __future__ import annotations

from game_session.auth.session_access import check_session_participation

__all__ = ["check_session_participation"]
