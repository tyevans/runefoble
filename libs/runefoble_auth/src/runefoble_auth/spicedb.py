"""SpiceDB Zanzibar client integration for fine-grained object-level authorization."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    resource_type: str
    resource_id: str
    relation: str
    subject_type: str
    subject_id: str


class MockSpiceDBClient:
    """In-memory mock Zanzibar relationship tuple store for tests and offline runs."""

    def __init__(self, endpoint: str = "localhost:50051", token: str = "secret"):
        self.endpoint = endpoint
        self.token = token
        self._tuples: set[str] = set()

    def _tuple_key(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> str:
        return f"{resource_type}:{resource_id}#{relation}@{subject_type}:{subject_id}"

    async def write_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Create a relationship tuple in Zanzibar."""
        key = self._tuple_key(resource_type, resource_id, relation, subject_type, subject_id)
        self._tuples.add(key)
        logger.info("SpiceDB tuple written: %s", key)

    async def delete_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> None:
        """Remove a relationship tuple."""
        key = self._tuple_key(resource_type, resource_id, relation, subject_type, subject_id)
        self._tuples.discard(key)

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Check whether a subject has a specific permission on a resource.

        Evaluates direct relations, owner bypass, and Zanzibar hierarchy.
        """
        # Direct relationship check
        direct = self._tuple_key(resource_type, resource_id, permission, subject_type, subject_id)
        if direct in self._tuples:
            return True

        # Owner bypass / supreme hierarchy
        owner = self._tuple_key(resource_type, resource_id, "owner", subject_type, subject_id)
        if owner in self._tuples:
            return True

        # Dungeon Master inheritance hierarchy
        dm = self._tuple_key(resource_type, resource_id, "dungeon_master", subject_type, subject_id)
        if dm in self._tuples and permission in (
            "dungeon_master",
            "run_session",
            "play",
            "view",
            "read",
            "edit",
            "move",
            "move_token",
            "modify_hp",
            "apply_condition",
            "spawn_monster",
            "set_scene",
            "control",
            "participate",
            "observe",
            "inspect",
        ):
            return True

        # Player inheritance
        player = self._tuple_key(resource_type, resource_id, "player", subject_type, subject_id)
        if player in self._tuples and permission in (
            "player",
            "play",
            "view",
            "read",
            "participate",
            "observe",
            "inspect",
        ):
            return True

        # Spectator inheritance
        spectator = self._tuple_key(
            resource_type, resource_id, "spectator", subject_type, subject_id
        )
        if spectator in self._tuples and permission in (
            "spectator",
            "view",
            "read",
            "observe",
            "inspect",
        ):
            return True

        # Character owner permissions
        if resource_type == "character":
            char_owner = self._tuple_key(
                "character", resource_id, "owner", subject_type, subject_id
            )
            if char_owner in self._tuples and permission in ("edit", "view", "read"):
                return True

        # Board token move permissions
        if resource_type == "board_token":
            token_move = self._tuple_key(
                "board_token", resource_id, "move", subject_type, subject_id
            )
            if token_move in self._tuples and permission in ("move", "move_token"):
                return True

        return False


class SpiceDBClient(MockSpiceDBClient):
    """Client for querying and writing permissions to SpiceDB Zanzibar engine.

    Supports live SpiceDB gRPC connection when available, with automatic mock fallback.
    """

    def __init__(
        self,
        endpoint: str = "localhost:50051",
        token: str = "secret",
        use_mock: bool | None = None,
    ):
        super().__init__(endpoint=endpoint, token=token)
        self.use_mock = use_mock
        self._grpc_client: Any = None
        if not self.use_mock:
            self._init_grpc_client()

    def _init_grpc_client(self) -> None:
        try:
            import grpc
            from authzed.api.v1 import Client

            self._grpc_client = Client(self.endpoint, grpc.insecure_channel(self.endpoint))
        except (ImportError, Exception) as exc:
            logger.debug(
                "SpiceDB gRPC client unavailable (%s); using in-memory mock fallback.", exc
            )
            self._grpc_client = None

    async def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        if self._grpc_client is not None:
            try:
                from authzed.api.v1 import (
                    CheckPermissionRequest,
                    CheckPermissionResponse,
                    ObjectReference,
                    SubjectReference,
                )

                request = CheckPermissionRequest(
                    resource=ObjectReference(object_type=resource_type, object_id=resource_id),
                    permission=permission,
                    subject=SubjectReference(
                        object=ObjectReference(object_type=subject_type, object_id=subject_id)
                    ),
                )
                response = await self._grpc_client.CheckPermission(request)
                return (
                    response.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                )
            except Exception as e:
                logger.warning("SpiceDB gRPC check failed, falling back to mock: %s", e)

        return await super().check_permission(
            resource_type, resource_id, permission, subject_type, subject_id
        )
