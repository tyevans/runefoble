"""LangGraph workflow for Natural Speech/Text to Game Intent parsing."""

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.models import ParsedAction


class IntentGraphState(TypedDict, total=False):
    request: dict[str, Any]
    normalized_transcript: str
    target_tokens: list[dict[str, Any]]
    raw_intent: dict[str, Any]
    parsed_action: dict[str, Any]
    error: str | None


def normalize_transcript_node(state: IntentGraphState) -> IntentGraphState:
    req = state["request"]
    raw_text = req.get("transcript", "")
    # Clean whitespace and strip leading filler phrases like "I want to", "Can I", "Um"
    cleaned = re.sub(
        r"^(um+|uh+|okay|so|hey watcher|i wanna|i want to|can i)\s+",
        "",
        raw_text,
        flags=re.IGNORECASE,
    ).strip()
    return {
        "normalized_transcript": cleaned,
        "target_tokens": req.get("visible_tokens", []),
    }


async def extract_candidate_action_node(
    state: IntentGraphState,
    llm_client: MultiBackendLLMClient,
) -> IntentGraphState:
    transcript = state.get("normalized_transcript", "")
    speaker_name = state["request"].get("speaker_name", "Player")
    visible_tokens = state.get("target_tokens", [])

    system_prompt = (
        "You are Runefoble's The Watcher Speech Parser. Convert player tabletop RPG declarations "
        "into structured JSON actions with fields: action_type, target_name, spell_or_ability, "
        "dice_check_required, narrative_flavor.\n"
        "action_type must be one of: attack, cast_spell, move, dash, dodge, help, skill_check, dialogue, unknown."
    )
    user_prompt = (
        f"Player: {speaker_name}\n"
        f"Transcript: {transcript}\n"
        f"Visible grid tokens: {json.dumps(visible_tokens)}\n"
        "Return valid JSON only."
    )

    extracted_dict: dict[str, Any] = {}
    if llm_client.active_backend != "mock":
        resp = await llm_client.generate_completion(system_prompt, user_prompt)
        content = resp.get("content", "")
        # Attempt to parse json from model output
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                extracted_dict = json.loads(match.group(0))
        except Exception:
            pass

    # Heuristic fallback if LLM returned empty or mock
    if not extracted_dict or not extracted_dict.get("action_type"):
        lower = transcript.lower()
        if any(w in lower for w in ["cast", "fireball", "missile", "cure", "heal", "spell"]):
            action_type = "cast_spell"
            spell = (
                "magic missile"
                if "magic missile" in lower
                else "fireball"
                if "fireball" in lower
                else "spell"
            )
            extracted_dict = {
                "action_type": action_type,
                "spell_or_ability": spell,
                "dice_check_required": "1d20+spell",
                "narrative_flavor": f"{speaker_name} weaves arcane energy into a somatic glyph.",
            }
        elif any(w in lower for w in ["attack", "strike", "slash", "shoot", "hit"]):
            extracted_dict = {
                "action_type": "attack",
                "spell_or_ability": "weapon_attack",
                "dice_check_required": "1d20+bonus",
                "narrative_flavor": f"{speaker_name} steps forward with weapon drawn.",
            }
        elif any(w in lower for w in ["move", "run", "step", "dash", "walk"]):
            extracted_dict = {
                "action_type": "move",
                "narrative_flavor": f"{speaker_name} advances across the stone tiles.",
            }
        else:
            extracted_dict = {
                "action_type": "dialogue"
                if any(w in lower for w in ["say", "tell", "whisper", "ask"])
                else "unknown",
                "narrative_flavor": f"{speaker_name}: '{transcript}'",
            }

    return {"raw_intent": extracted_dict}


def resolve_spatial_and_targets_node(state: IntentGraphState) -> IntentGraphState:
    raw = state.get("raw_intent", {})
    transcript = state.get("normalized_transcript", "")
    tokens = state.get("target_tokens", [])

    target_token_id = None
    target_token_name = raw.get("target_name")
    target_x = raw.get("target_x")
    target_y = raw.get("target_y")

    # Match target against visible tokens by name substring
    lower_transcript = transcript.lower()
    for tok in tokens:
        name = tok.get("name", "").lower()
        if name and (
            name in lower_transcript or (target_token_name and name in target_token_name.lower())
        ):
            target_token_id = tok.get("token_id")
            target_token_name = tok.get("name")
            target_x = tok.get("x")
            target_y = tok.get("y")
            break

    # Check for coordinate mentions (e.g. "move to 4, 7" or "(4,7)")
    coord_match = re.search(r"\b(\d+)\s*[,x\s]\s*(\d+)\b", transcript)
    if coord_match:
        target_x = int(coord_match.group(1))
        target_y = int(coord_match.group(2))

    action_type = raw.get("action_type", "unknown")
    if action_type not in [
        "attack",
        "cast_spell",
        "move",
        "dash",
        "dodge",
        "help",
        "skill_check",
        "dialogue",
        "unknown",
    ]:
        action_type = "unknown"

    parsed = ParsedAction(
        action_type=action_type,
        target_token_id=target_token_id,
        target_token_name=target_token_name,
        target_x=target_x,
        target_y=target_y,
        spell_or_ability=raw.get("spell_or_ability"),
        dice_check_required=raw.get("dice_check_required"),
        confidence=0.95 if target_token_id or target_x is not None else 0.85,
        narrative_flavor=raw.get("narrative_flavor", ""),
        raw_transcript=state["request"].get("transcript", ""),
    )

    return {"parsed_action": parsed.model_dump()}


def build_intent_graph(llm_client: MultiBackendLLMClient):
    workflow = StateGraph(IntentGraphState)

    workflow.add_node("normalize", normalize_transcript_node)

    async def candidate_node(state: IntentGraphState):
        return await extract_candidate_action_node(state, llm_client)

    workflow.add_node("extract_candidate", candidate_node)
    workflow.add_node("resolve_spatial", resolve_spatial_and_targets_node)

    workflow.add_edge(START, "normalize")
    workflow.add_edge("normalize", "extract_candidate")
    workflow.add_edge("extract_candidate", "resolve_spatial")
    workflow.add_edge("resolve_spatial", END)

    return workflow.compile()
