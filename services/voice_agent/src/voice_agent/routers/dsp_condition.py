"""Speech text conditioning route for affliction DSP filters (TASK-0675).

Returns conditioned text and DSP filter parameters. It never returns audio.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from voice_agent.dependencies import dsp_pipeline

router = APIRouter(tags=["Voice DSP Conditioning"])


class DSPConditionRequest(BaseModel):
    text: str = Field(min_length=1)
    filters: list[str] = Field(default_factory=list)


class DSPConditionResponse(BaseModel):
    original_text: str
    conditioned_text: str
    active_filters: list[str] = Field(default_factory=list)
    dsp_config: dict[str, Any] = Field(default_factory=dict)


@router.post("/api/v1/voice/dsp/condition", response_model=DSPConditionResponse)
async def condition_speech_text(req: DSPConditionRequest) -> DSPConditionResponse:
    """Apply affliction text transforms and compute DSP filter parameters for speech text."""
    result = dsp_pipeline.process(req.text, req.filters)
    return DSPConditionResponse(
        original_text=result.original_text,
        conditioned_text=result.conditioned_text,
        active_filters=result.active_filters,
        dsp_config=result.dsp_config.model_dump(),
    )
