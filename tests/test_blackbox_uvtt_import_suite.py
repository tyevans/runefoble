"""Universal VTT Importer & Dynamic FastMCP Registry blackbox test suite shim.

Maintains backward compatibility by re-exporting decomposed test suites.
Governed by TASK-0193 and ADR-0003.
"""

from __future__ import annotations

from tests.test_blackbox_uvtt_import.conftest import (
    board_client,
    build_sample_dd2vtt_dict,
    clean_environment,
    gateway_client,
)
from tests.test_blackbox_uvtt_import.test_dynamic_mcp_registry import (
    test_blackbox_dynamic_mcp_sandbox_rejection_security,
    test_blackbox_dynamic_mcp_tool_lifecycle,
    test_blackbox_dynamic_mcp_tool_registration_and_execution,
)
from tests.test_blackbox_uvtt_import.test_uvtt_map_import import (
    test_blackbox_uvtt_invalid_payload_error,
    test_blackbox_uvtt_json_direct_payload,
    test_blackbox_uvtt_multipart_file_upload,
)

__all__ = [
    "board_client",
    "build_sample_dd2vtt_dict",
    "clean_environment",
    "gateway_client",
    "test_blackbox_dynamic_mcp_sandbox_rejection_security",
    "test_blackbox_dynamic_mcp_tool_lifecycle",
    "test_blackbox_dynamic_mcp_tool_registration_and_execution",
    "test_blackbox_uvtt_invalid_payload_error",
    "test_blackbox_uvtt_json_direct_payload",
    "test_blackbox_uvtt_multipart_file_upload",
]
