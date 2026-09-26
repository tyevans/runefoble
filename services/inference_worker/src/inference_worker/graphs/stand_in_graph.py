"""LangGraph workflow for Missing Player Stand-in AI with penalties."""

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from inference_worker.llm_client import MultiBackendLLMClient
from inference_worker.models import StandInActionResponse


class StandInGraphState(TypedDict, total=False):
    request: dict[str, Any]
    penalty_effects: list[str]
    action_decision: dict[str, Any]
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


async def generate_stand_in_decision_node(
    state: StandInGraphState,
    llm_client: MultiBackendLLMClient,
) -> StandInGraphState:
    req = state["request"]
    char_name = req.get("character_name", "Hero")
    char_class = req.get("character_class", "Fighter")
    traits = req.get("personality_traits", ["brave"])
    penalties = req.get("penalties", [])
    penalty_effects = state.get("penalty_effects", [])
    scene_context = req.get("scene_context", "In combat")
    enemies = req.get("visible_enemies", [])
    guardrails = req.get("guardrails", {})

    guardrail_notes = []
    if guardrails:
        if guardrails.get("preserve_spell_slots"):
            guardrail_notes.append(f"Preserve spell slots: {guardrails['preserve_spell_slots']}")
        if guardrails.get("protect_allies"):
            guardrail_notes.append(f"Protect allies: {', '.join(guardrails['protect_allies'])}")
        if guardrails.get("avoid_melee"):
            guardrail_notes.append("Avoid frontline melee engagement")
        if guardrails.get("custom_priorities"):
            guardrail_notes.append(
                f"Custom priorities: {'; '.join(guardrails['custom_priorities'])}"
            )

    system_prompt = (
        "You are Runefoble's Absent Player Stand-in AI. "
        "A player is missing from game night, so you autonomously pilot their character. "
        "Faithfully reflect their class and personality, BUT you MUST comically and mechanically "
        "incorporate any DM-inflicted penalties (like 'drunk' or 'foolishness') and MUST respect "
        "any player-configured tactical guardrails (e.g. preserving high level slots, protecting allies).\n"
        "Return a JSON object with: action_type, target, dialogue, narrative_flavor, mechanics."
    )
    user_prompt = (
        f"Character: {char_name} ({char_class})\n"
        f"Traits: {', '.join(traits)}\n"
        f"DM Penalties: {', '.join(penalties) if penalties else 'None'}\n"
        f"Penalty Manifestation: {'; '.join(penalty_effects)}\n"
        f"Tactical Guardrails: {'; '.join(guardrail_notes) if guardrail_notes else 'None'}\n"
        f"Scene: {scene_context}\n"
        f"Enemies: {', '.join(enemies) if enemies else 'Unknown threats'}\n"
        "Generate their turn action and in-character spoken dialogue."
    )

    decision = {}
    if llm_client.active_backend != "mock":
        resp = await llm_client.generate_completion(system_prompt, user_prompt)
        content = resp.get("content", "")
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                decision = json.loads(match.group(0))
        except Exception:
            pass

    # Heuristic fallback if LLM returned empty or mock
    if not decision or not decision.get("action_type"):
        target = enemies[0] if enemies else "nearest foe"
        protect_allies = guardrails.get("protect_allies", []) if guardrails else []
        avoid_melee = guardrails.get("avoid_melee", False) if guardrails else False

        if protect_allies and (
            any(a.lower() in scene_context.lower() for a in protect_allies)
            or "heal" in scene_context.lower()
        ):
            target_ally = protect_allies[0]
            action_type = "cast_spell"
            if "drunk" in [p.lower() for p in penalties]:
                dialogue = f"*Hic* 'Hold on {target_ally}! Healing light incoming!' *burp*"
                flavor = f"{char_name} sways wildly while channeling healing magic on {target_ally} per guardrails."
                mechanics = {
                    "action": "heal",
                    "target": target_ally,
                    "penalty": "drunk",
                    "guardrail": "protect_allies",
                }
            else:
                dialogue = f"'Protecting {target_ally}! Stand fast!'"
                flavor = f"{char_name} casts protective healing on {target_ally} obeying tactical guardrails."
                mechanics = {"action": "heal", "target": target_ally, "guardrail": "protect_allies"}
        elif avoid_melee and char_class.lower() in [
            "cleric",
            "wizard",
            "sorcerer",
            "ranger",
            "druid",
        ]:
            action_type = "cast_spell" if char_class.lower() != "ranger" else "ranged_attack"
            dialogue = "'Keeping distance from frontline melee as planned!'"
            flavor = f"{char_name} maintains safe distance, deploying ranged attacks per tactical guardrails."
            mechanics = {"action": action_type, "target": target, "guardrail": "avoid_melee"}
        elif "drunk" in [p.lower() for p in penalties]:
            action_type = "attack"
            dialogue = (
                "*Hic* 'Stand shtill, ya six-eyed fiend! I got two blades and one of 'em'sh real!'"
            )
            flavor = (
                f"{char_name} sways dangerously on one boot, attempting a wide overhand strike at {target} "
                "before stumbling into a nearby barrel."
            )
            mechanics = {
                "roll": "1d20-2",
                "condition": "Disadvantage (Intoxicated)",
                "penalty": "drunk",
            }
        elif "foolishness" in [p.lower() for p in penalties]:
            action_type = "foolish_act"
            dialogue = "'Observe my masterstroke! Never flank when you can charge directly through their spears!'"
            flavor = (
                f"{char_name} boldly announces their tactical plan at the top of their lungs, "
                f"waving arms wildly to draw all enemy attention."
            )
            mechanics = {
                "action": "distraction",
                "penalty": "foolishness",
                "hostile_advantage_granted": True,
            }
        else:
            action_type = (
                "attack"
                if char_class.lower() in ["fighter", "barbarian", "rogue", "paladin"]
                else "cast_spell"
            )
            dialogue = "'For the realm! Stand firm!'"
            flavor = f"{char_name} executes a textbook {char_class} maneuver against {target}."
            mechanics = {"action": action_type, "target": target}

        decision = {
            "action_type": action_type,
            "target": target,
            "dialogue": dialogue,
            "narrative_flavor": flavor,
            "mechanics": mechanics,
        }

    return {"action_decision": decision}


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
    )
    return {"final_response": resp.model_dump()}


def build_stand_in_graph(llm_client: MultiBackendLLMClient):
    workflow = StateGraph(StandInGraphState)

    workflow.add_node("evaluate_penalties", evaluate_penalties_node)

    async def dec_node(state: StandInGraphState):
        return await generate_stand_in_decision_node(state, llm_client)

    workflow.add_node("generate_decision", dec_node)
    workflow.add_node("compile", compile_stand_in_response_node)

    workflow.add_edge(START, "evaluate_penalties")
    workflow.add_edge("evaluate_penalties", "generate_decision")
    workflow.add_edge("generate_decision", "compile")
    workflow.add_edge("compile", END)

    return workflow.compile()
