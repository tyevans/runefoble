"""Validate, map, and propose the steps of an agent action plan (TASK-0747).

`run_plan` runs the steps in order and stops at the first step that fails. Each step passes
four stages in this order:

1. `plan_step` maps the raw action to a `StepRequest`. It reads one key per field.
2. `validate_step` checks the tool name and the actor name. It makes no call.
3. The `authorize` port checks the schema permission of the step.
4. The `propose` port sends the step to The Watcher.

The module imports no FastMCP and no HTTP client. The caller passes its ports.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from gateway_mcp.owning_services import ServiceError

ToolExists = Callable[[str], bool]
Authorize = Callable[[str, dict[str, Any]], Awaitable[None]]
Propose = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

UNKNOWN_TOOL = "unknown"


class PlanStepError(Exception):
    """A step that cannot run. `str(exc)` is the message that the caller sees."""

    def __init__(self, message: str, tool: str) -> None:
        super().__init__(message)
        self.tool = tool


@dataclass(frozen=True)
class StepRequest:
    """One plan step after mapping. Its fields match the request that The Watcher receives."""

    tool: str
    actor_name: str
    description: str
    target: str | None
    parameters: dict[str, Any]


@dataclass(frozen=True)
class PlanPorts:
    """The ports that the runner needs. The caller supplies them."""

    tool_exists: ToolExists
    authorize: Authorize
    propose: Propose


def plan_step(action: dict[str, Any]) -> StepRequest:
    """Map one raw action to a `StepRequest`. A missing or malformed field fails the step."""
    tool = action.get("tool")
    if not tool:
        raise PlanStepError("Action missing 'tool' specification", UNKNOWN_TOOL)
    tool_name = str(tool)
    raw = action.get("parameters")
    if raw is None:
        parameters: dict[str, Any] = {}
    elif isinstance(raw, dict):
        parameters = dict(raw)
    else:
        raise PlanStepError("Action 'parameters' must be an object", tool_name)
    target = parameters.get("target", parameters.get("token_id"))
    return StepRequest(
        tool=tool_name,
        actor_name=str(action.get("actor_name") or ""),
        description=str(action.get("description") or tool_name),
        target=str(target) if target is not None else None,
        parameters=parameters,
    )


def validate_step(step: StepRequest, tool_exists: ToolExists) -> None:
    """Check that the tool exists and that the step names an actor. Makes no call."""
    if not tool_exists(step.tool):
        raise PlanStepError(f"Invalid tool: '{step.tool}' not found", step.tool)
    if not step.actor_name:
        raise PlanStepError("Action missing 'actor_name' specification", step.tool)


def to_watcher_request(step: StepRequest, session_id: str, campaign_id: str) -> dict[str, Any]:
    """Return the body of `POST /api/v1/watcher/actions/propose` for one step."""
    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "actor_name": step.actor_name,
        "action_type": step.tool,
        "description": step.description,
        "target": step.target,
        "parameters": step.parameters,
    }


async def run_plan(
    actions: list[dict[str, Any]],
    *,
    session_id: str,
    campaign_id: str,
    ports: PlanPorts,
) -> dict[str, Any]:
    """Run the steps in order. Stop at the first failed step and return the plan report."""
    run = _PlanRun(session_id=session_id, campaign_id=campaign_id, total=len(actions))
    for idx, action in enumerate(actions):
        try:
            step = plan_step(action)
            validate_step(step, ports.tool_exists)
            await ports.authorize(step.tool, step.parameters)
        except PlanStepError as exc:
            return run.failed(idx, exc.tool, str(exc))
        started = time.perf_counter()
        try:
            output = await ports.propose(to_watcher_request(step, session_id, campaign_id))
        except ServiceError as exc:
            return run.failed(idx, step.tool, str(exc), _elapsed_ms(started))
        run.succeeded(idx, step.tool, output, _elapsed_ms(started))
    return run.finished()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


@dataclass
class _PlanRun:
    """The step ledger of one plan run. It builds the response shape that clients pin."""

    session_id: str
    campaign_id: str
    total: int
    steps: list[dict[str, Any]] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def succeeded(self, idx: int, tool: str, output: dict[str, Any], duration: float) -> None:
        self.total_duration_ms += duration
        self.steps.append(
            {
                "step": idx + 1,
                "tool": tool,
                "status": "success",
                "output": output,
                "duration_ms": duration,
            }
        )

    def failed(self, idx: int, tool: str, error: str, duration: float = 0.0) -> dict[str, Any]:
        self.steps.append(
            {
                "step": idx + 1,
                "tool": tool,
                "status": "error",
                "error": error,
                "duration_ms": duration,
            }
        )
        return {
            "status": "error",
            "success": False,
            "session_id": self.session_id,
            "campaign_id": self.campaign_id,
            "error": error,
            "failed_step": idx + 1,
            "total_steps": self.total,
            "completed_steps": idx,
            "steps": self.steps,
            "total_duration_ms": round(self.total_duration_ms + duration, 2),
        }

    def finished(self) -> dict[str, Any]:
        return {
            "status": "success",
            "success": True,
            "session_id": self.session_id,
            "campaign_id": self.campaign_id,
            "total_steps": self.total,
            "completed_steps": self.total,
            "steps": self.steps,
            "total_duration_ms": round(self.total_duration_ms, 2),
        }
