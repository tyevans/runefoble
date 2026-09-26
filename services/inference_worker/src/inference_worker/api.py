"""FastAPI application for Runefoble AI Inference Worker."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from inference_worker.config import WorkerSettings
from inference_worker.graphs import build_intent_graph, build_narration_graph, build_stand_in_graph
from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.models import (
    DMNarrationRequest,
    DMNarrationResponse,
    IntentParseRequest,
    IntentParseResponse,
    ParsedAction,
    StandInActionRequest,
    StandInActionResponse,
)
from inference_worker.redis_consumer import RedisInferenceConsumer

# Global runtime state
settings = WorkerSettings()
llm_client = MultiBackendLLMClient(settings)
intent_graph = None
narration_graph = None
stand_in_graph = None
redis_consumer: RedisInferenceConsumer | None = None


def ensure_graphs():
    global intent_graph, narration_graph, stand_in_graph
    if intent_graph is None:
        intent_graph = build_intent_graph(llm_client)
    if narration_graph is None:
        narration_graph = build_narration_graph(llm_client)
    if stand_in_graph is None:
        stand_in_graph = build_stand_in_graph(llm_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_consumer

    # Detect backend and compile LangGraph pipelines
    await llm_client.detect_available_backend()
    ensure_graphs()

    # Start optional background Redis stream listener
    redis_consumer = RedisInferenceConsumer(settings, llm_client)
    await redis_consumer.start()

    yield

    if redis_consumer:
        await redis_consumer.stop()


app = FastAPI(
    title="Runefoble AI Inference Worker",
    version="0.1.0",
    description="Distributed LangGraph-based inference engine for natural speech parsing, DM narration, and stand-in AI.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
@app.get("/health")
async def health_check():
    """Health check reporting active backend status."""
    return {
        "status": "healthy",
        "service": "inference_worker",
        "backend": llm_client.active_backend,
        "openai_model": settings.openai_model,
        "ollama_model": settings.ollama_model,
    }


@app.post("/inference/v1/intent", response_model=IntentParseResponse)
async def parse_intent(req: IntentParseRequest):
    """Parse natural speech or text into structured tabletop RPG game action."""
    start_time = time.perf_counter()
    ensure_graphs()
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
    )


@app.post("/inference/v1/dm-narration", response_model=DMNarrationResponse)
async def generate_dm_narration(req: DMNarrationRequest):
    """Generate rich sensory scene description and DM options based on recent game events."""
    ensure_graphs()
    if narration_graph is None:
        raise HTTPException(status_code=503, detail="Narration graph not initialized")

    state = await narration_graph.ainvoke({"request": req.model_dump()})
    final_dict = state.get("final_response", {})
    return DMNarrationResponse(**final_dict)


@app.post("/inference/v1/stand-in-action", response_model=StandInActionResponse)
async def decide_stand_in_action(req: StandInActionRequest):
    """Simulate tactical action and dialogue for absent player incorporating DM penalties."""
    ensure_graphs()
    if stand_in_graph is None:
        raise HTTPException(status_code=503, detail="Stand-in graph not initialized")

    state = await stand_in_graph.ainvoke({"request": req.model_dump()})
    final_dict = state.get("final_response", {})
    return StandInActionResponse(**final_dict)
