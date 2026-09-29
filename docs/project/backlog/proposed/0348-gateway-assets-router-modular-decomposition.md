---
id: '0348'
title: Gateway Assets Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0023
- TASK-0045
- TASK-0067
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0013
governing_stories:
- US-0031
- US-0043
target_release: 0.8.0
---

# TASK-0348: Gateway Assets Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/assets.py` (277 lines, 55.4% of limit) into modular submodules under `gateway/api/src/gateway_api/assets/` (`models.py`, `upload.py`, `operations.py`, `router.py`), with an aggregator export at `gateway/api/src/gateway_api/assets.py`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`gateway/api/src/gateway_api/assets.py` consolidates Pydantic upload models, authentication header extraction, multi-format media stream ingestion (JSON base64, multipart/form-data, and raw binary streaming), Silo S3 object storage invocation, metadata querying, streaming download piping, deletion operations, and Redis Streams domain event broadcasting (`AssetUploaded`, `AssetDeleted`) in a single monolithic router file. As additional asset transforms (such as WebP token thumbnailing, audio stem transcoding, and battlemap LOD tiling) are introduced, this file will approach the 500-line limit unless modularized into focused components.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and isolated test execution.
- **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing across service aggregates.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Code formatting and linting standards.
- **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Asset Models & Utilities (`gateway/api/src/gateway_api/assets/models.py`)**:
   - Extract `AssetUploadRequest`, `AssetMetadataResponse`, `AssetDeleteResponse`, `_sanitize_filename`, and `_resolve_user_id` (< 80 lines).
2. **Media Upload Handler (`gateway/api/src/gateway_api/assets/upload.py`)**:
   - Extract `POST /upload` endpoint supporting multipart/form-data, base64 JSON, and binary streams, publishing `AssetUploaded` events (< 110 lines).
3. **Asset Operations & Streaming (`gateway/api/src/gateway_api/assets/operations.py`)**:
   - Extract `GET /{asset_id}`, `GET /{asset_id}/download`, and `DELETE /{asset_id}` with `AssetDeleted` event publishing (< 100 lines).
4. **Router Aggregator (`gateway/api/src/gateway_api/assets/router.py`)**:
   - Combine endpoints into an APIRouter (< 40 lines).
5. **Backwards-Compatible Entry Point (`gateway/api/src/gateway_api/assets.py`)**:
   - Re-export `router`, models, and helpers for existing callers (< 30 lines).
6. **Verification**:
   - Verify `uv run pytest tests/test_silo_storage.py` and all related gateway tests pass with 100% success.

## Definition of Done
- `gateway/api/src/gateway_api/assets/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `assets.py` reduced to a backwards-compatible re-export module (< 40 lines).
- 100% pass rate on `uv run pytest tests/test_silo_storage.py`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
