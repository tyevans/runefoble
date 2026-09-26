"""LangGraph workflow for The Watcher Autonomous DM Narration."""

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.models import DMNarrationResponse


class NarrationGraphState(TypedDict, total=False):
    request: dict[str, Any]
    context_summary: str
    narration_text: str
    sensory_details: list[str]
    suggested_prompts: list[str]
    tension_level: str
    final_response: dict[str, Any]


def analyze_context_node(state: NarrationGraphState) -> NarrationGraphState:
    req = state["request"]
    recent = req.get("recent_events", [])
    env = req.get("scene_environment", "Dungeon chamber")
    tone = req.get("tone", "dark_fantasy")

    context_summary = f"Setting: {env} | Tone: {tone} | Recent Events: {'; '.join(recent[-5:]) if recent else 'Exploration started'}"

    # Simple heuristic tension analysis
    lower_events = " ".join(recent).lower()
    if any(k in lower_events for k in ["critical", "unconscious", "died", "boss", "collapse"]):
        tension = "climax"
    elif any(k in lower_events for k in ["attack", "damage", "initiative", "hostile", "trap"]):
        tension = "rising"
    elif any(k in lower_events for k in ["rest", "safe", "loot", "campfire"]):
        tension = "aftermath"
    else:
        tension = "calm"

    return {
        "context_summary": context_summary,
        "tension_level": tension,
    }


async def generate_narration_node(
    state: NarrationGraphState,
    llm_client: MultiBackendLLMClient,
) -> NarrationGraphState:
    req = state["request"]
    env = req.get("scene_environment", "Ancient vault")
    tone = req.get("tone", "dark_fantasy")
    prompt = req.get("guidance_prompt") or "Describe the unfolding moment."
    summary = state.get("context_summary", "")

    system_prompt = (
        "You are The Watcher, the AI co-DM for Runefoble. "
        "Provide rich, atmospheric, sensory narration for the tabletop roleplaying scene. "
        "Never dictate player decisions or outcomes; describe the environment and consequences vividly. "
        "Return a JSON object with: narration, sensory_details (list of strings), suggested_dm_prompts (list of strings)."
    )
    user_prompt = (
        f"Context: {summary}\n"
        f"Environment: {env}\n"
        f"Tone: {tone}\n"
        f"Guidance Request: {prompt}\n"
        "Generate evocative scene narration."
    )

    narration = ""
    sensory = []
    suggested = []

    if llm_client.active_backend != "mock":
        resp = await llm_client.generate_completion(system_prompt, user_prompt)
        content = resp.get("content", "")
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                narration = data.get("narration", "")
                sensory = data.get("sensory_details", [])
                suggested = data.get("suggested_dm_prompts", [])
        except Exception:
            pass

    if not narration:
        narration = (
            f"A heavy silence settles over the {env.lower()}. "
            f"{prompt}. Shadows dance along the jagged walls as unseen draughts stir the stale air."
        )
        sensory = [
            "The metallic tang of ozone and old blood",
            "The distant, rhythmic drip of subterranean water",
            "A sudden draft extinguishing torch flames",
        ]
        suggested = [
            "Ask players to make a DC 13 Perception check",
            "Introduce an echoing skittering from the northern passage",
            "Reveal a concealed inscription glowing faintly on the altar",
        ]

    return {
        "narration_text": narration,
        "sensory_details": sensory,
        "suggested_prompts": suggested,
    }


def compile_narration_node(state: NarrationGraphState) -> NarrationGraphState:
    req = state["request"]
    resp = DMNarrationResponse(
        session_id=req.get("session_id", ""),
        narration=state.get("narration_text", ""),
        sensory_details=state.get("sensory_details", []),
        suggested_dm_prompts=state.get("suggested_prompts", []),
        tension_level=state.get("tension_level", "rising"),
    )
    return {"final_response": resp.model_dump()}


def build_narration_graph(llm_client: MultiBackendLLMClient):
    workflow = StateGraph(NarrationGraphState)

    workflow.add_node("analyze_context", analyze_context_node)

    async def gen_node(state: NarrationGraphState):
        return await generate_narration_node(state, llm_client)

    workflow.add_node("generate_narration", gen_node)
    workflow.add_node("compile", compile_narration_node)

    workflow.add_edge(START, "analyze_context")
    workflow.add_edge("analyze_context", "generate_narration")
    workflow.add_edge("generate_narration", "compile")
    workflow.add_edge("compile", END)

    return workflow.compile()
