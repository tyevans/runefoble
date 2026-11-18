"""The voice agent's Redis Streams event bus provider, shared by its pipelines and routers."""

from __future__ import annotations

from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider

event_bus_provider = EventBusProvider(PlatformSettings())
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set
