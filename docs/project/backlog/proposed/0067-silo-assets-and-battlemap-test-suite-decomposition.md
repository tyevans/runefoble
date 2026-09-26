---
id: '0067'
title: Silo S3 Media Asset Bucket Storage and Battlemap Pipeline Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0023, TASK-0031]
governing_adrs: [ADR-0003, ADR-0013]
target_release: 0.2.0
---

# TASK-0067: Silo S3 Media Asset Bucket Storage and Battlemap Pipeline Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_silo_assets.py` (362 lines, 72.4% of limit) into two specialized test suites (`tests/test_blackbox_silo_asset_lifecycle.py` and `tests/test_blackbox_silo_asset_events.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new media asset formats and storage capabilities are added.

## Problem Statement
`tests/test_blackbox_silo_assets.py` currently spans 362 lines. It bundles multiple disparate test domains into a single test file:
1. CloudEvents 1.0 schema compliance and registry verification (`test_asset_events_registration_and_cloudevents`).
2. Blackbox file upload handling across both multipart/form-data and JSON base64 payloads for avatars, battlemaps, and audio tracks (`test_blackbox_upload_*`).
3. Binary streaming, metadata retrieval, and attachment download header verification (`test_blackbox_get_asset_metadata_and_streaming`).
4. MIME type validation, max payload size boundaries (10MB limit), and empty payload rejections (`test_blackbox_rejection_*`).
5. Asset deletion lifecycle and subsequent 404 responses (`test_blackbox_delete_asset_and_subsequent_404`).
6. Domain event emission over distributed Redis Streams and in-memory event buses (`test_blackbox_event_emission_on_upload_and_delete`).
7. OpenAPI documentation hub route inspection (`test_openapi_documentation_includes_asset_routes`).

As campaign handouts, audio clips, token frames, and upload chunking are introduced in upcoming milestones, this file is poised to surpass the 500-line ceiling.

## Proposed Decomposition
1. **Asset Lifecycle & Validation Suite (`tests/test_blackbox_silo_asset_lifecycle.py`)**:
   - Multipart and JSON base64 uploads for avatar and battlemap images.
   - Metadata queries, direct binary streaming (`/stream`), and download headers (`/download`).
   - Rejections: invalid MIME types, oversize payloads (>10MB), and empty payloads.
   - Deletion lifecycle and 404 response verification (< 200 lines).
2. **Asset Domain Events & OpenAPI Suite (`tests/test_blackbox_silo_asset_events.py`)**:
   - CloudEvents 1.0 compliance and EventRegistry registration for `AssetUploaded` and `AssetDeleted`.
   - Redis Streams stream publishing (`runefoble.events.asset`) and in-memory platform bus delivery.
   - OpenAPI `/openapi.json` route schema presence and method declarations (< 170 lines).
3. **Shared Test Fixtures & Constants (`tests/conftest.py` or `tests/helpers/silo_fixtures.py`)**:
   - Common sample byte constants (`PNG_SAMPLE_BYTES`, `WAV_SAMPLE_BYTES`) and `clean_storage_and_bus` isolation fixture.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without changing production asset routing or storage mechanics.
- **Negotiable (N)**: Distribution between lifecycle and event test files can be adjusted.
- **Valuable (V)**: Prevents Hard Invariant 6 violations (< 500 lines) and improves blackbox test maintainability.
- **Estimable (E)**: Pure pytest module splitting with shared fixture support.
- **Small (S)**: Scope isolated strictly to `tests/test_blackbox_silo_assets.py`; all resulting files < 200 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_silo_*.py`.

## Acceptance Criteria
1. `tests/test_blackbox_silo_assets.py` decomposed into focused modules strictly under 220 lines each.
2. 100% test pass rate on all 11 existing asset test scenarios with zero regressions.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP endpoints and published domain events.
