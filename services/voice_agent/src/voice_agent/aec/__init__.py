"""Acoustic Echo Cancellation (AEC) DSP Module (TASK-0169).

Exports NLMS adaptive filter, Double-Talk Detector, and unified AECPipeline.
"""

from __future__ import annotations

from voice_agent.aec.double_talk import DoubleTalkDetector, DoubleTalkState, ResidualEchoSuppressor
from voice_agent.aec.nlms_filter import NLMSAECFilter
from voice_agent.aec.pipeline import AECPipeline

__all__ = [
    "AECPipeline",
    "DoubleTalkDetector",
    "DoubleTalkState",
    "NLMSAECFilter",
    "ResidualEchoSuppressor",
]
