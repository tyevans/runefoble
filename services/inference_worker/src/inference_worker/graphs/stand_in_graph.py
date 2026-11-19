"""LangGraph workflow for Missing Player Stand-in AI with penalties."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from runefoble_platform.stand_in_guardrails import GuardrailName, StandInGuardrailPolicy

from inference_worker.model_output import parse_json_object, require_field
from inference_worker.models import ResponseSource, StandInActionResponse
from inference_worker.ports import Completion, LLMPort


class StandInGraphState(TypedDict, total=False):
    request: dict[str, Any]
    penalty_effects: list[str]
    action_decision: dict[str, Any]
    source: ResponseSource
    guardrails_applied: list[GuardrailName]
    final_response: dict[str, Any]


def evaluate_penalties_node(state: StandInGraphState) -> StandInGraphState:
    req = state["request"]
    penalties = [p.lower().strip() for p in req.get("penalties", [])]
    effects = []

    if "drunk" in penalties:
        effects.append(
            "Slurred speech, stumbling gait, disadvantage on Dexterity and attack rolls."
        )
    if "foolishness" in penalties:
        effects.append(
            "Comically poor tactical judgment, reckless bravado, ignoring obvious hazards."
        )
    if "cowardice" in penalties:
        effects.append(
            "Evasive posturing, seeking cover behind companions, reluctance to enter melee."
        )
    if not effects:
        effects.append("Normal tactical competence matching character class.")

    return {"penalty_effects": effects}


def _prompt_guardrail_notes(policy: StandInGuardrailPolicy) -> dict[GuardrailName, str]:
    """One prompt note per active guardrail, keyed by the guardrail name."""
    notes: dict[GuardrailName, str] = {}
    if policy.preserve_spell_slots:
        notes[GuardrailName.PRESERVE_SPELL_SLOTS] = (
            f"Preserve spell slots: {policy.preserve_spell_slots}"
        )
    if policy.protect_allies:
        notes[GuardrailName.PROTECT_ALLIES] = f"Protect allies: {', '.join(policy.protect_allies)}"
    if policy.avoid_melee:
        notes[GuardrailName.AVOID_MELEE] = "Avoid frontline melee engagement"
    if policy.custom_priorities:
        notes[GuardrailName.CUSTOM_PRIORITIES] = (
            f"Custom priorities: {'; '.join(policy.custom_priorities)}"
        )
    return notes


STAND_IN_SYSTEM_PROMPT = (
    "You are Runefoble's Absent Player Stand-in AI. "
    "A player is missing from game night, so you autonomously pilot their character. "
    "Faithfully reflect their class and personality, BUT you MUST comically and mechanically "
    "incorporate any DM-inflicted penalties (like 'drunk' or 'foolishness') and MUST respect "
    "any player-configured tactical guardrails (e.g. preserving high level slots, protecting allies).\n"
    "Return a JSON object with: action_type, target, dialogue, narrative_flavor, mechanics, "
    "guardrails_applied (the names of the guardrails you followed)."
)


def _stand_in_user_prompt(
    req: dict[str, Any], penalty_effects: list[str], guardrail_notes: dict[GuardrailName, str]
) -> str:
    char_name = req.get("character_name", "Hero")
    char_class = req.get("character_class", "Fighter")
    traits = req.get("personality_traits", ["brave"])
    penalties = req.get("penalties", [])
    scene_context = req.get("scene_context", "In combat")
    enemies = req.get("visible_enemies", [])
    return (
        f"Character: {char_name} ({char_class})\n"
        f"Traits: {', '.join(traits)}\n"
        f"DM Penalties: {', '.join(penalties) if penalties else 'None'}\n"
        f"Penalty Manifestation: {'; '.join(penalty_effects)}\n"
        f"Tactical Guardrails: {'; '.join(guardrail_notes.values()) if guardrail_notes else 'None'}\n"
        f"Scene: {scene_context}\n"
        f"Enemies: {', '.join(enemies) if enemies else 'Unknown threats'}\n"
        "Generate their turn action and in-character spoken dialogue."
    )


def _decision_from_completion(
    completion: Completion, guardrail_notes: dict[GuardrailName, str]
) -> tuple[dict[str, Any], list[GuardrailName]]:
    """Read the decision. Keep only the guardrail names that the request activated."""
    decision = parse_json_object(completion.content)
    require_field(decision, "action_type", completion.backend)
    declared = decision.get("guardrails_applied")
    applied = [g for g in declared if g in guardrail_notes] if isinstance(declared, list) else []
    return decision, applied


async def generate_stand_in_decision_node(
    state: StandInGraphState,
    llm_port: LLMPort,
) -> StandInGraphState:
    req = state["request"]
    policy = StandInGuardrailPolicy.model_validate(req.get("guardrails") or {})
    guardrail_notes = _prompt_guardrail_notes(policy)
    user_prompt = _stand_in_user_prompt(req, state.get("penalty_effects", []), guardrail_notes)

    # Raises EngineUnavailableError when the engine fails or the output has no action_type.
    completion = await llm_port.complete(STAND_IN_SYSTEM_PROMPT, user_prompt)
    decision, applied = _decision_from_completion(completion, guardrail_notes)
    return {
        "action_decision": decision,
        "source": "llm",
        "guardrails_applied": applied,
    }


def compile_stand_in_response_node(state: StandInGraphState) -> StandInGraphState:
    req = state["request"]
    dec = state.get("action_decision", {})

    action_type = dec.get("action_type", "attack")
    if action_type not in ["attack", "cast_spell", "move", "flee", "foolish_act", "blunder"]:
        action_type = "attack"

    resp = StandInActionResponse(
        session_id=req.get("session_id", ""),
        character_name=req.get("character_name", "Hero"),
        action_type=action_type,
        target=dec.get("target"),
        dialogue=dec.get("dialogue", "..."),
        narrative_flavor=dec.get("narrative_flavor", ""),
        penalties_applied=req.get("penalties", []),
        mechanics=dec.get("mechanics", {}),
        guardrails_applied=state.get("guardrails_applied", []),
        source=state["source"],
    )
    return {"final_response": resp.model_dump()}


def build_stand_in_graph(llm_port: LLMPort):
    workflow = StateGraph(StandInGraphState)

    workflow.add_node("evaluate_penalties", evaluate_penalties_node)

    async def dec_node(state: StandInGraphState):
        return await generate_stand_in_decision_node(state, llm_port)

    workflow.add_node("generate_decision", dec_node)
    workflow.add_node("compile", compile_stand_in_response_node)

    workflow.add_edge(START, "evaluate_penalties")
    workflow.add_edge("evaluate_penalties", "generate_decision")
    workflow.add_edge("generate_decision", "compile")
    workflow.add_edge("compile", END)

    return workflow.compile()
