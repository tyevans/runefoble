"""The Zanzibar relationship tuple value type that every SpiceDB client returns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Relationship:
    """One relationship tuple: `resource_type:resource_id#relation@subject_type:subject_id`."""

    resource_type: str
    resource_id: str
    relation: str
    subject_type: str
    subject_id: str

    def to_tuple_key(self) -> str:
        return f"{self.resource_type}:{self.resource_id}#{self.relation}@{self.subject_type}:{self.subject_id}"

    @classmethod
    def from_tuple_key(cls, key: str) -> Relationship:
        res, rest = key.split("#", 1)
        res_t, res_id = res.split(":", 1)
        rel, subj = rest.split("@", 1)
        sub_t, sub_id = subj.split(":", 1)
        return cls(res_t, res_id, rel, sub_t, sub_id)
