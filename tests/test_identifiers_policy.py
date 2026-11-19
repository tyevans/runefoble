"""Unit tests for the shared identifier policy (TASK-0731, ADR-0015).

A missing or malformed id is an error. No helper draws a random id.
"""

from __future__ import annotations

from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import pytest
from runefoble_platform.identifiers import (
    InvalidIdentifierError,
    opaque_aggregate_id,
    opaque_optional_aggregate_id,
    parse_optional_uuid,
    parse_uuid,
)


def test_parse_uuid_accepts_uuid_and_uuid_text():
    value = uuid4()
    assert parse_uuid(value, field="campaign_id") == value
    assert parse_uuid(str(value), field="campaign_id") == value


@pytest.mark.parametrize("bad", [None, "", "not-a-uuid"])
def test_parse_uuid_rejects_missing_or_malformed_value(bad):
    with pytest.raises(InvalidIdentifierError) as err:
        parse_uuid(bad, field="campaign_id")
    assert err.value.status_code == 400
    assert "campaign_id" in err.value.detail


def test_opaque_id_keeps_a_uuid_and_maps_text_through_uuid5():
    value = uuid4()
    assert opaque_aggregate_id(value, field="session_id") == value
    assert opaque_aggregate_id(str(value), field="session_id") == value
    assert opaque_aggregate_id("sess-1", field="session_id") == uuid5(NAMESPACE_DNS, "sess-1")


def test_opaque_id_is_stable_across_calls():
    first = opaque_aggregate_id("sess-stable", field="session_id")
    second = opaque_aggregate_id("sess-stable", field="session_id")
    assert isinstance(first, UUID)
    assert first == second


@pytest.mark.parametrize("missing", [None, ""])
def test_opaque_id_rejects_a_missing_value(missing):
    with pytest.raises(InvalidIdentifierError):
        opaque_aggregate_id(missing, field="session_id")


@pytest.mark.parametrize("missing", [None, ""])
def test_optional_helpers_carry_null_for_a_missing_value(missing):
    assert parse_optional_uuid(missing, field="campaign_id") is None
    assert opaque_optional_aggregate_id(missing, field="campaign_id") is None


def test_optional_uuid_still_rejects_a_malformed_value():
    with pytest.raises(InvalidIdentifierError):
        parse_optional_uuid("not-a-uuid", field="campaign_id")
