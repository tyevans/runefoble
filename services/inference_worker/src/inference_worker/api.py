"""FastAPI application for Runefoble AI Inference Worker."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from runefoble_platform.engine_ports import EngineUnavailableError
from runefoble_platform.event_publish import event_publish_failures

from inference_worker.auth import service_credential_guard
from inference_worker.config import WorkerSettings
from inference_worker.graphs import build_intent_graph, build_narration_graph, build_stand_in_graph
from inference_worker.llm_factory import build_llm_port
from inference_worker.models import (
    DMNarrationRequest,
    DMNarrationResponse,
    IntentParseRequest,
    IntentParseResponse,
    ParsedAction,
    StandInActionRequest,
    StandInActionResponse,
)
from inference_worker.ports import LLMPort

# Global runtime state. The lifespan selects the LLM port once and builds the graphs for it.
settings = WorkerSettings.from_environment()
llm_port: LLMPort | None = None
intent_graph = None
narration_graph = None
stand_in_graph = None


def set_llm_port(port: LLMPort) -> None:
    """Make `port` the engine for every graph. The lifespan calls this once at start-up."""
    global llm_port, intent_graph, narration_graph, stand_in_graph
    llm_port = port
    intent_graph = build_intent_graph(port)
    narration_graph = build_narration_graph(port)
    stand_in_graph = build_stand_in_graph(port)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Build the engine and refuse to start when it does not answer (ADR-0015 decision 4)."""
    port = build_llm_port(settings)
    await port.check_ready()
    set_llm_port(port)
    yield


app = FastAPI(
    title="Runefoble AI Inference Worker",
    version="0.1.0",
    description="Distributed LangGraph-based inference engine for natural speech parsing, DM narration, and stand-in AI.",
    lifespan=lifespan,
)

# The worker is server-to-server only. It sends no CORS headers, so browsers cannot call it.
inference_router = APIRouter(
    prefix="/inference/v1",
    dependencies=[
        Depends(service_credential_guard(settings.service_credential.get_secret_value()))
    ],
)


app.include_router(inference_router)


@app.exception_handler(EngineUnavailableError)
async def backend_unavailable_handler(
    _request: Request, exc: EngineUnavailableError
) -> JSONResponse:
    """Report a failed model engine as an explicit 503. Never return substitute output.

    The worker keeps its published flat body. See the response contract reference.
    """
    return JSONResponse(
        status_code=503,
        content={"error": exc.error_code, "backend": exc.engine},
    )


@app.get("/healthz")
async def health_check():
    """Health check reporting active backend status."""
    return {
        "status": "healthy",
        "service": "inference_worker",
        "backend": settings.backend,
        "openai_model": settings.openai_model,
        "ollama_model": settings.ollama_model,
        "event_publish_failures": event_publish_failures(),
    }


@inference_router.post("/intent", response_model=IntentParseResponse)
async def parse_intent(req: IntentParseRequest):
    """Parse natural speech or text into structured tabletop RPG game action."""
    start_time = time.perf_counter()
    if intent_graph is None:
        raise HTTPException(status_code=503, detail="Intent graph not initialized")

    state = await intent_graph.ainvoke({"request": req.model_dump()})
    action_dict = state.get("parsed_action", {})
    action = ParsedAction(**action_dict)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return IntentParseResponse(
        session_id=req.session_id,
        speaker_name=req.speaker_name,
        action=action,
        execution_time_ms=round(elapsed_ms, 2),
        source=state["source"],
        degraded=state["degraded"],
    )


@inference_router.post("/dm-narration", response_model=DMNarrationResponse)
async def generate_dm_narration(req: DMNarrationRequest):
    """Generate rich sensory scene description and DM options based on recent game events."""
    if narration_graph is None:
        raise HTTPException(status_code=503, detail="Narration graph not initialized")

    state = await narration_graph.ainvoke({"request": req.model_dump()})
    final_dict = state.get("final_response", {})
    return DMNarrationResponse(**final_dict)


@inference_router.post("/stand-in-action", response_model=StandInActionResponse)
async def decide_stand_in_action(req: StandInActionRequest):
    """Simulate tactical action and dialogue for absent player incorporating DM penalties."""
    if stand_in_graph is None:
        raise HTTPException(status_code=503, detail="Stand-in graph not initialized")

    state = await stand_in_graph.ainvoke({"request": req.model_dump()})
    final_dict = state.get("final_response", {})
    return StandInActionResponse(**final_dict)
