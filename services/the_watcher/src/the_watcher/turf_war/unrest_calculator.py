"""Regional unrest metric tracker computing escalation, security levels, and economic friction."""

from __future__ import annotations


class UnrestCalculator:
    """Calculates town unrest indices, security alertness, and economic friction metrics."""

    @staticmethod
    def calculate_alert_level(unrest_score: int) -> str:
        """Derive regional alert level from 0-100 unrest score."""
        score = max(0, min(100, unrest_score))
        if score <= 20:
            return "calm"
        if score <= 45:
            return "guarded"
        if score <= 70:
            return "elevated"
        if score <= 85:
            return "high"
        return "critical"

    @staticmethod
    def calculate_security_level(alert_level: str) -> str:
        """Derive guard deployment and town security posture from alert level."""
        mapping = {
            "calm": "standard",
            "guarded": "patrolled",
            "elevated": "heightened",
            "high": "curfew",
            "critical": "martial_law",
        }
        return mapping.get(alert_level.lower(), "standard")

    @staticmethod
    def calculate_economic_friction(unrest_score: int) -> float:
        """Calculate market price friction and smuggling risk modifier (0.0 to 1.0)."""
        score = max(0, min(100, unrest_score))
        return round(min(1.0, max(0.0, score / 100.0 * 0.9)), 2)

    @classmethod
    def calculate_escalation(
        cls, current_unrest: int, unrest_delta: int
    ) -> tuple[int, str, str, float]:
        """Compute new unrest score, alert level, security posture, and economic friction."""
        new_unrest = max(0, min(100, current_unrest + unrest_delta))
        alert = cls.calculate_alert_level(new_unrest)
        security = cls.calculate_security_level(alert)
        friction = cls.calculate_economic_friction(new_unrest)
        return new_unrest, alert, security, friction

    @staticmethod
    def decay_unrest(current_unrest: int, peace_ticks: int = 1, decay_per_tick: int = 5) -> int:
        """Simulate natural unrest stabilization during peaceful intervals."""
        return max(0, current_unrest - (peace_ticks * decay_per_tick))


unrest_calculator = UnrestCalculator()
