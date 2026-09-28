pytest_plugins = [
    "tests.helpers.audio_synth",
    "tests.helpers.postgres",
    "tests.helpers.prd_fixtures",
    "tests.helpers.silo_fixtures",
    "tests.helpers.spicedb",
    "tests.helpers.zitadel_auth",
]
collect_ignore = ["test_blackbox_uvtt_import.py"]
