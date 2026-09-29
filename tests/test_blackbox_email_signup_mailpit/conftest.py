"""Shared fixtures for Mailpit email signup and auth blackbox test suite."""

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from gateway_api.routers.auth import (
    _pending_verifications,
    get_mailpit_client,
    set_mailpit_client,
)
from runefoble_platform.email_client import MailpitClient


@pytest.fixture(autouse=True)
def reset_mailpit_state():
    """Ensure clean Mailpit client and verification state before each test."""
    client = MailpitClient(fallback_in_memory=True)
    set_mailpit_client(client)
    _pending_verifications.clear()
    yield client
    client.sent_emails.clear()
    _pending_verifications.clear()


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI TestClient bound to the gateway application."""
    return TestClient(app)


@pytest.fixture
def mailpit() -> MailpitClient:
    """Provide the active Mailpit client instance for inspection."""
    return get_mailpit_client()
