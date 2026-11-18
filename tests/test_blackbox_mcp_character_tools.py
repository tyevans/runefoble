"""Blackbox tests for the gateway MCP character tools (TASK-0604).

The seven character tools call the character_sheet service over HTTP. The
tests run the real character_sheet app on a loopback port (ADR-0014). Setup
uses the public character_sheet routes. Assertions read the public sheet route.
Nothing patches the HTTP client or writes private service state.
"""

import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from character_sheet.main import app as character_app
from gateway_mcp.server import mcp
from mcp.types import CallToolResult

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.ws_identity import SIGNING_ISSUER

_MCP: dict[str, str] = {}
_CAMPAIGN: dict[str, str] = {}


@pytest.fixture(scope="module", autouse=True)
def character_service() -> Iterator[str]:
    """Run character_sheet as a real HTTP service for the gateway tools."""
    with pytest.MonkeyPatch.context() as env, serve(character_app) as url:
        env.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", url)
        yield url


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so that each call carries the caller bearer."""
    with serve_mcp(mcp) as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


@pytest.fixture(autouse=True)
def campaign(game_session_upstream: str) -> Iterator[str]:
    """Create a campaign through game_session. `mcp-tester` owns it, so it runs the sessions."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('mcp-tester')}"}
    with httpx.Client(base_url=game_session_upstream, headers=headers) as http:
        res = http.post("/api/v1/campaigns", json={"title": "Tool Campaign", "setting": "Test"})
        assert res.status_code == 201, res.text
        _CAMPAIGN["id"] = res.json()["id"]
    yield _CAMPAIGN["id"]
    _CAMPAIGN.clear()


@pytest.fixture
def sheet_http(character_service: str) -> Iterator[httpx.Client]:
    """Frontdoor HTTP client for the character_sheet service, with a signed owner token."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('mcp-tester')}"}
    with httpx.Client(base_url=character_service, headers=headers) as http:
        yield http


def create_character(http: httpx.Client, name: str, character_class: str, max_hp: int) -> str:
    """Create a character through the public character_sheet route and return its id."""
    res = http.post(
        "/api/v1/characters",
        json={"name": name, "character_class": character_class, "max_hp": max_hp},
    )
    assert res.status_code == 200, res.text
    character_id = str(res.json()["character_id"])
    # Put the character in the campaign, so that the campaign DM may act on it.
    assigned = http.patch(
        f"/api/v1/characters/{character_id}/campaign", json={"campaign_id": _CAMPAIGN["id"]}
    )
    assert assigned.status_code == 200, assigned.text
    return character_id


def read_sheet(http: httpx.Client, character_id: str) -> dict[str, Any]:
    """Read the stored character through the public sheet route."""
    res = http.get(f"/api/v1/characters/{character_id}")
    assert res.status_code == 200, res.text
    data: dict[str, Any] = res.json()
    return data


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Call a tool over MCP HTTP as `mcp-tester`, the owner of the character and the campaign."""
    return await call_tool_over_http(
        _MCP["url"], name, arguments, SIGNING_ISSUER.mint("mcp-tester")
    )


def tool_text(result: CallToolResult) -> str:
    """Return the text of the first content block of a tool result."""
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


def tool_payload(result: CallToolResult) -> dict[str, Any]:
    """Return the JSON payload of a successful tool result."""
    assert not result.isError, f"Tool failed: {tool_text(result)}"
    data = json.loads(tool_text(result))
    assert isinstance(data, dict)
    return data


@pytest.mark.asyncio
async def test_modify_character_hp_change_is_visible_in_character_sheet_route(sheet_http):
    """HP changed through MCP equals the HP read back through the sheet route."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)

    payload = tool_payload(
        await call_tool(
            "modify_character_hp",
            {"character_id": character_id, "delta": -5, "reason": "Goblin blade"},
        )
    )

    assert payload["current_hp"] == 40
    assert payload["max_hp"] == 45
    assert read_sheet(sheet_http, character_id)["current_hp"] == 40


@pytest.mark.asyncio
async def test_get_character_sheet_returns_stored_character_not_fixed_data(sheet_http):
    """get_character_sheet returns the stored name, class and HP for the id."""
    character_id = create_character(sheet_http, "Kyra", "Cleric", max_hp=30)

    sheet = tool_payload(await call_tool("get_character_sheet", {"character_id": character_id}))

    assert sheet["character_id"] == character_id
    assert sheet["name"] == "Kyra"
    assert sheet["class"] == "Cleric"
    assert sheet["hp"] == {"current": 30, "max": 30}
    assert "Valeros" not in tool_text(
        await call_tool("get_character_sheet", {"character_id": character_id})
    )


@pytest.mark.asyncio
async def test_get_character_sheet_unknown_id_is_tool_error():
    """An id with no character returns a tool error from the upstream 404."""
    result = await call_tool("get_character_sheet", {"character_id": str(uuid4())})

    assert result.isError is True
    assert "404" in tool_text(result)
    assert "Valeros" not in tool_text(result)


@pytest.mark.asyncio
async def test_get_character_sheet_malformed_id_is_tool_error():
    """A non-UUID id such as the old fixture 'char-1' is rejected, not answered."""
    result = await call_tool("get_character_sheet", {"character_id": "char-1"})

    assert result.isError is True
    assert "char-1" in tool_text(result)


@pytest.mark.asyncio
async def test_apply_condition_is_visible_in_character_sheet_route(sheet_http):
    """A condition applied through MCP appears on the sheet read through the route."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)

    payload = tool_payload(
        await call_tool(
            "apply_condition",
            {
                "character_id": character_id,
                "condition": "Prone",
                "duration_rounds": 2,
                "source": "Shove",
            },
        )
    )

    assert payload["status"] == "condition_applied"
    assert payload["condition"] == "prone"
    stored = read_sheet(sheet_http, character_id)["conditions"]
    assert "prone" in stored
    assert stored["prone"]["duration_rounds"] == 2
    assert stored["prone"]["source"] == "Shove"


@pytest.mark.asyncio
async def test_add_condition_is_visible_in_character_sheet_route(sheet_http):
    """add_condition persists through the same route as apply_condition."""
    character_id = create_character(sheet_http, "Kyra", "Cleric", max_hp=30)

    tool_payload(
        await call_tool("add_condition", {"character_id": character_id, "condition": "blinded"})
    )

    assert "blinded" in read_sheet(sheet_http, character_id)["conditions"]


@pytest.mark.asyncio
async def test_apply_absentee_penalty_is_visible_in_character_sheet_route(sheet_http):
    """A session miss penalty applied through MCP appears in the sheet penalties."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)

    payload = tool_payload(
        await call_tool(
            "apply_absentee_penalty",
            {
                "character_id": character_id,
                "penalty_type": "drunk",
                "explanation": "Drank excessive tavern cider",
            },
        )
    )

    assert payload["status"] == "applied"
    assert payload["penalty_type"] == "drunk"
    stored = read_sheet(sheet_http, character_id)["penalties"]
    assert stored == {"drunk": "Drank excessive tavern cider"}


@pytest.mark.asyncio
async def test_cast_spell_expends_slot_visible_in_character_sheet_route(sheet_http):
    """Each cast through MCP spends a slot, and an empty slot level is rejected."""
    character_id = create_character(sheet_http, "Kyra", "Cleric", max_hp=30)

    first = tool_payload(
        await call_tool(
            "cast_spell",
            {"character_id": character_id, "spell_name": "Cure Wounds", "spell_level": 1},
        )
    )
    assert first["status"] == "cast"
    assert read_sheet(sheet_http, character_id)["spell_slots"]["1"] == 1

    tool_payload(
        await call_tool(
            "cast_spell",
            {"character_id": character_id, "spell_name": "Shield", "spell_level": 1},
        )
    )
    assert read_sheet(sheet_http, character_id)["spell_slots"]["1"] == 0

    exhausted = await call_tool(
        "cast_spell",
        {"character_id": character_id, "spell_name": "Shield", "spell_level": 1},
    )
    assert exhausted.isError is True
    assert "INSUFFICIENT_SPELL_SLOTS" in tool_text(exhausted)
    assert read_sheet(sheet_http, character_id)["spell_slots"]["1"] == 0


@pytest.mark.asyncio
async def test_inspect_inventory_reads_items_added_through_inventory_routes(sheet_http):
    """Inventory and equipment written through the sheet routes are read back by MCP."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)
    added = sheet_http.post(
        f"/api/v1/characters/{character_id}/inventory",
        json={"item_id": "healing-potion", "name": "Healing Potion", "quantity": 2},
    )
    assert added.status_code == 200, added.text
    equipped = sheet_http.post(
        f"/api/v1/characters/{character_id}/equipment",
        json={"slot": "main_hand", "item_name": "Longsword +1"},
    )
    assert equipped.status_code == 200, equipped.text

    payload = tool_payload(await call_tool("inspect_inventory", {"character_id": character_id}))

    assert payload["character_id"] == character_id
    assert payload["equipped"] == {"main_hand": "Longsword +1"}
    potions = [item for item in payload["inventory"] if item["item_id"] == "healing-potion"]
    assert len(potions) == 1
    assert potions[0]["name"] == "Healing Potion"
    assert potions[0]["quantity"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("get_character_sheet", {"character_id": "PLACEHOLDER"}),
        ("inspect_inventory", {"character_id": "PLACEHOLDER"}),
        (
            "apply_absentee_penalty",
            {"character_id": "PLACEHOLDER", "penalty_type": "drunk", "explanation": "x"},
        ),
        ("cast_spell", {"character_id": "PLACEHOLDER", "spell_name": "Shield", "spell_level": 1}),
        ("modify_character_hp", {"character_id": "PLACEHOLDER", "delta": -5}),
        ("add_condition", {"character_id": "PLACEHOLDER", "condition": "prone"}),
        ("apply_condition", {"character_id": "PLACEHOLDER", "condition": "prone"}),
    ],
)
async def test_character_tools_return_error_when_character_service_returns_503(
    monkeypatch, sheet_http, tool, arguments
):
    """Every character tool returns an error result when character_sheet answers 503."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)
    arguments = {**arguments, "character_id": character_id}
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", down_url)
        result = await call_tool(tool, arguments)

    assert result.isError is True
    assert "503" in tool_text(result)


@pytest.mark.asyncio
async def test_modify_character_hp_returns_error_when_character_service_is_unreachable(
    monkeypatch, sheet_http
):
    """An unreachable character_sheet is a tool error, not a substitute HP value."""
    character_id = create_character(sheet_http, "Valeros", "Fighter", max_hp=45)
    monkeypatch.setenv("RUNEFOBLE_CHARACTER_SHEET_URL", closed_port_url())
    result = await call_tool("modify_character_hp", {"character_id": character_id, "delta": -5})

    assert result.isError is True
    assert "unreachable" in tool_text(result)
    assert "new_hp" not in tool_text(result)
