"""Unit and integration tests for decomposed mock SpiceDB submodules."""

import pytest
from runefoble_auth.mock import (
    MockSpiceDBClient,
    PermissionEvaluator,
    load_default_schema,
    parse_zed_schema,
)


def test_schema_parser_and_graph() -> None:
    schema_text = """
    definition document {
        relation writer: user
        relation reader: user
        permission write = writer
        permission view = write + reader
    }
    """
    graph = parse_zed_schema(schema_text)
    assert "document" in graph.definitions
    doc_def = graph.definitions["document"]
    assert "writer" in doc_def.relations
    assert graph.get_permission_rules("document", "view") == ["write", "reader"]
    assert graph.get_relation_types("document", "writer") == ["user"]


def test_load_default_schema() -> None:
    graph = load_default_schema()
    assert "campaign" in graph.definitions
    assert "character" in graph.definitions
    assert "board_token" in graph.definitions


@pytest.mark.asyncio
async def test_evaluator_direct_and_caveat() -> None:
    evaluator = PermissionEvaluator(caveats={"ip_check": lambda ctx: ctx.get("ip") == "127.0.0.1"})
    assert evaluator.evaluate_caveat("ip_check", {"ip": "127.0.0.1"}) is True
    assert evaluator.evaluate_caveat("ip_check", {"ip": "10.0.0.1"}) is False
    assert evaluator.evaluate_caveat("unknown", None) is True

    tuples = {"doc:1#view@user:alice"}
    assert await evaluator.evaluate(tuples, "doc", "1", "view", "user", "alice") is True
    assert await evaluator.evaluate(tuples, "doc", "1", "view", "user", "bob") is False


@pytest.mark.asyncio
async def test_mock_spicedb_client_crud_and_touch() -> None:
    client = MockSpiceDBClient()
    await client.write_relationship("campaign", "c1", "player", "user", "u1")
    rels = await client.read_relationships(resource_type="campaign", relation="player")
    assert len(rels) == 1
    assert rels[0].subject_id == "u1"

    await client.touch_relationship("campaign", "c1", "player", "user", "u1")
    assert await client.check_permission("campaign", "c1", "view", "user", "u1") is True

    await client.delete_relationship("campaign", "c1", "player", "user", "u1")
    assert await client.check_permission("campaign", "c1", "view", "user", "u1") is False


@pytest.mark.asyncio
async def test_mock_client_schema_update() -> None:
    client = MockSpiceDBClient()
    custom_schema = """
    definition post {
        relation author: user
        permission edit = author
    }
    """
    await client.write_schema(custom_schema)
    assert await client.read_schema() == custom_schema
    await client.write_relationship("post", "p1", "author", "user", "u_author")
    assert await client.check_permission("post", "p1", "edit", "user", "u_author") is True
    assert await client.check_permission("post", "p1", "edit", "user", "u_other") is False
