"""Campaign Analytics APIRouters."""

from campaign_analytics.routers.heatmap import router as heatmap_router
from campaign_analytics.routers.mvp import router as mvp_router
from campaign_analytics.routers.timeline import router as timeline_router

__all__ = ["heatmap_router", "mvp_router", "timeline_router"]
