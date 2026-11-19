"""Top-level pytest configuration for every test folder in the repository.

It lives at the repository root, so `pytest_plugins` applies to `tests/`, `gateway/api/tests/`
and the package test folders, whichever folder a run starts from.
"""

import os

import pytest
from runefoble_platform.config import PlatformSettings
from runefoble_platform.service_client import OWNER_URL_FIELDS

from tests.helpers.container_owner import remove_orphaned_test_containers

# Test mode: the SpiceDB preshared key has no default outside tests. Tests supply a throwaway
# value before any settings object is built. Live tests may override it in their environment.
os.environ.setdefault("RUNEFOBLE_SPICEDB_PRESHARED_KEY", "test-only-spicedb-key")
# Service URLs have no code defaults. Unless a test sets one itself, these point at a closed
# loopback port, so no test reaches a real service by accident.
# The environment name is the settings alias when the field has one (the_watcher_url reads
# RUNEFOBLE_WATCHER_URL), else the RUNEFOBLE_ prefix and the field name.
for _field in OWNER_URL_FIELDS.values():
    _alias = PlatformSettings.model_fields[_field].validation_alias
    _names = getattr(_alias, "choices", None) or ["RUNEFOBLE_" + _field.upper()]
    for _name in _names:
        os.environ.setdefault(_name, "http://127.0.0.1:9")
# The inference worker refuses to start without its service token (ADR-0015 e). Tests use a
# throwaway value. Process-level tests remove it from the child environment on purpose.
os.environ.setdefault("RUNEFOBLE_SERVICE_CREDENTIAL", "test-only-service-credential")
# Tests select the in-memory event store explicitly. The platform default is PostgreSQL, and a
# deployed environment refuses memory (TASK-0707). Tests that need PostgreSQL pass settings.
os.environ["RUNEFOBLE_EVENT_STORE_BACKEND"] = "memory"
# The Watcher defaults to its inference worker (TASK-0741). Tests that need the local rule engine
# select it here. Tests that need the worker set the worker URL themselves with monkeypatch.
os.environ.setdefault("RUNEFOBLE_WATCHER_ENGINE", "heuristic")


def pytest_sessionstart(session):
    """Remove test containers whose owner process died in an earlier run. Live owners are kept."""
    remove_orphaned_test_containers()


# These modules check wall-clock time or start a browser. Under heavy parallel load they fail
# for reasons that are not defects. They carry the `serial` marker, and the gate runs them
# after the parallel run, one at a time: see `make test`.
SERIAL_MODULES = frozenset(
    {
        "tests/test_blackbox_adaptive_stream/test_adaptive_stream.py",
        "tests/test_blackbox_app_shell_test_modular_decomposition.py",
        "tests/test_blackbox_audience_studio_durability.py",
        "tests/test_blackbox_barge_in_filter/test_barge_in_filter.py",
        "tests/test_blackbox_campaign_lore_rag.py",
        "tests/test_blackbox_dev_environment.py",
        "tests/test_blackbox_ghost_previews.py",
        "tests/test_blackbox_intent_disambiguation_flow.py",
        "tests/test_blackbox_leitmotif_api.py",
        "tests/test_blackbox_leitmotif_triggers.py",
        "tests/test_blackbox_mobile_companion.py",
        "tests/test_blackbox_mobile_companion_ui.py",
        "tests/test_blackbox_plugin_slots/test_plugin_slots.py",
        "tests/test_blackbox_rules_compendium.py",
        "tests/test_blackbox_rules_compendium_ui/test_srd_search.py",
        "tests/test_blackbox_spell_vfx/test_speech_vfx_triggers.py",
        "tests/test_blackbox_spell_vfx/test_spell_adjudication.py",
        "tests/test_blackbox_streaming_whisper_e2e.py",
        "tests/test_blackbox_streaming_whisper_vad.py",
        "tests/test_blackbox_vocal_modulator/test_vocal_modulator.py",
        "tests/test_blackbox_voice_agent/test_voice_duplex_controls_ui.py",
        "tests/test_blackbox_voice_dsp.py",
        "tests/test_blackbox_voice_duplex.py",
        "tests/test_blackbox_voice_telemetry.py",
        "tests/test_blackbox_webrtc_routing.py",
        "tests/test_speech_to_intent.py",
        "tests/test_voice_agent_dsp.py",
    }
)


def pytest_collection_modifyitems(config, items):
    """Mark every test in SERIAL_MODULES as `serial`."""
    root = config.rootpath
    for item in items:
        if item.path.relative_to(root).as_posix() in SERIAL_MODULES:
            item.add_marker(pytest.mark.serial)


pytest_plugins = [
    "tests.realtime_session",
    "tests.helpers.audio_synth",
    "tests.helpers.campaign_analytics_service",
    "tests.helpers.campaign_setup",
    "tests.helpers.event_store_seam",
    "tests.helpers.lore_backends",
    "tests.helpers.module_state",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.restart_stack",
    "tests.helpers.service_harness",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spectator_table",
    "tests.helpers.spicedb",
    "tests.helpers.stand_in_policy",
    "tests.helpers.voice_identity",
    "tests.helpers.voice_signaling",
    "tests.helpers.zitadel_auth",
]
