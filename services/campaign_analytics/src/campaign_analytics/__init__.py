"""Runefoble Campaign Analytics & Chronicle Archive bounded context."""

from campaign_analytics.event_handlers import AnalyticsEventDispatcher, handle_domain_event
from campaign_analytics.worker import CampaignAnalyticsWorker

__version__ = "0.1.0"
__all__ = [
    "AnalyticsEventDispatcher",
    "CampaignAnalyticsWorker",
    "handle_domain_event",
]
