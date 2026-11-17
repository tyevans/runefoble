"""Contract tests for object names that the schema must define (TASK-0540)."""

from runefoble_auth.mock import load_default_schema


def test_character_defines_delete_permission_from_owner() -> None:
    graph = load_default_schema()
    assert "delete" in graph.definitions["character"].permissions
    assert graph.get_permission_rules("character", "delete") == ["owner"]


def test_codex_entry_defines_party_shared_and_public_relations() -> None:
    graph = load_default_schema()
    codex = graph.definitions["codex_entry"]
    assert graph.get_relation_types("codex_entry", "party_shared") == ["campaign"]
    assert graph.get_relation_types("codex_entry", "public") == ["campaign"]
    assert "party_shared" in codex.relations
    assert "public" in codex.relations


def test_codex_entry_view_includes_campaign_privacy_levels() -> None:
    graph = load_default_schema()
    assert graph.get_permission_rules("codex_entry", "view") == [
        "author",
        "editor",
        "reader",
        "party_shared->play",
        "public->view",
    ]


def test_system_type_is_not_defined() -> None:
    graph = load_default_schema()
    assert "system" not in graph.definitions


def test_campaign_has_no_viewer_relation() -> None:
    graph = load_default_schema()
    assert "viewer" not in graph.definitions["campaign"].relations
