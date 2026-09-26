"""Tests verifying modular decomposition and backward compatibility of runefoble_platform.analytics."""

from __future__ import annotations


def test_import_from_subpackage_facade() -> None:
    """Verify that importing from runefoble_platform.analytics exposes all public symbols."""
    from runefoble_platform.analytics import (
        FORBIDDEN_PROPERTY_KEYS,
        AnalyticsEventWorker,
        OpenPanelClient,
        anonymize_profile_id,
        sanitize_properties,
    )

    assert OpenPanelClient is not None
    assert AnalyticsEventWorker is not None
    assert callable(anonymize_profile_id)
    assert callable(sanitize_properties)
    assert "audio" in FORBIDDEN_PROPERTY_KEYS


def test_import_from_modular_submodules() -> None:
    """Verify that importing directly from modular subpackages works as expected."""
    from runefoble_platform.analytics.client import OpenPanelClient
    from runefoble_platform.analytics.privacy import (
        FORBIDDEN_PROPERTY_KEYS,
        anonymize_profile_id,
        sanitize_properties,
    )
    from runefoble_platform.analytics.worker import AnalyticsEventWorker

    assert OpenPanelClient is not None
    assert AnalyticsEventWorker is not None
    assert callable(anonymize_profile_id)
    assert callable(sanitize_properties)
    assert "audio" in FORBIDDEN_PROPERTY_KEYS


def test_import_from_backward_compatibility_aliases() -> None:
    """Verify backward compatibility sibling modules re-export identical symbols."""
    from runefoble_platform.analytics.client import OpenPanelClient
    from runefoble_platform.analytics.privacy import (
        FORBIDDEN_PROPERTY_KEYS,
        anonymize_profile_id,
        sanitize_properties,
    )
    from runefoble_platform.analytics.worker import AnalyticsEventWorker
    from runefoble_platform.analytics_client import OpenPanelClient as ClientAlias
    from runefoble_platform.analytics_privacy import (
        FORBIDDEN_PROPERTY_KEYS as FORBIDDEN_ALIAS,
    )
    from runefoble_platform.analytics_privacy import (
        anonymize_profile_id as anonymize_alias,
    )
    from runefoble_platform.analytics_privacy import (
        sanitize_properties as sanitize_alias,
    )
    from runefoble_platform.analytics_worker import (
        AnalyticsEventWorker as WorkerAlias,
    )

    assert ClientAlias is OpenPanelClient
    assert WorkerAlias is AnalyticsEventWorker
    assert anonymize_alias is anonymize_profile_id
    assert sanitize_alias is sanitize_properties
    assert FORBIDDEN_ALIAS is FORBIDDEN_PROPERTY_KEYS
