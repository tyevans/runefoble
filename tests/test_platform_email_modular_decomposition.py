"""Tests verifying modular decomposition and backward compatibility of runefoble_platform.email."""

from __future__ import annotations

from pathlib import Path


def test_import_from_subpackage_facade() -> None:
    """Verify that importing from runefoble_platform.email exposes all public symbols."""
    from runefoble_platform.email import (
        EmailMessage,
        EmailRecipient,
        EmailVerificationPayload,
        MailpitClient,
        MailpitMessage,
        MailpitMessageSummary,
        OutboundEmail,
        SmtpTransport,
        build_mime_message,
        extract_verification_code,
        extract_verification_link,
    )

    assert MailpitClient is not None
    assert SmtpTransport is not None
    assert OutboundEmail is not None
    assert MailpitMessage is not None
    assert MailpitMessageSummary is not None
    assert EmailRecipient is not None
    assert EmailMessage is not None
    assert EmailVerificationPayload is not None
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_import_from_modular_submodules() -> None:
    """Verify that importing directly from modular submodules works as expected."""
    from runefoble_platform.email.mailpit import MailpitClient
    from runefoble_platform.email.models import (
        EmailMessage,
        EmailRecipient,
        EmailVerificationPayload,
        MailpitMessage,
        MailpitMessageSummary,
        OutboundEmail,
        extract_verification_code,
        extract_verification_link,
    )
    from runefoble_platform.email.smtp import SmtpTransport, build_mime_message

    assert MailpitClient is not None
    assert SmtpTransport is not None
    assert OutboundEmail is not None
    assert MailpitMessage is not None
    assert MailpitMessageSummary is not None
    assert EmailRecipient is not None
    assert EmailMessage is not None
    assert EmailVerificationPayload is not None
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_import_from_backward_compatibility_shim() -> None:
    """Verify backward compatibility shim email_client.py re-exports identical symbols."""
    from runefoble_platform.email import (
        EmailMessage as FacadeMessage,
    )
    from runefoble_platform.email import (
        EmailRecipient as FacadeRecipient,
    )
    from runefoble_platform.email import (
        EmailVerificationPayload as FacadePayload,
    )
    from runefoble_platform.email import (
        MailpitClient as FacadeClient,
    )
    from runefoble_platform.email import (
        MailpitMessage as FacadeMailpitMessage,
    )
    from runefoble_platform.email import (
        MailpitMessageSummary as FacadeSummary,
    )
    from runefoble_platform.email import (
        OutboundEmail as FacadeOutbound,
    )
    from runefoble_platform.email import (
        SmtpTransport as FacadeTransport,
    )
    from runefoble_platform.email_client import (
        EmailMessage as ShimMessage,
    )
    from runefoble_platform.email_client import (
        EmailRecipient as ShimRecipient,
    )
    from runefoble_platform.email_client import (
        EmailVerificationPayload as ShimPayload,
    )
    from runefoble_platform.email_client import (
        MailpitClient as ShimClient,
    )
    from runefoble_platform.email_client import (
        MailpitMessage as ShimMailpitMessage,
    )
    from runefoble_platform.email_client import (
        MailpitMessageSummary as ShimSummary,
    )
    from runefoble_platform.email_client import (
        OutboundEmail as ShimOutbound,
    )
    from runefoble_platform.email_client import (
        SmtpTransport as ShimTransport,
    )
    from runefoble_platform.email_client import (
        build_mime_message,
        extract_verification_code,
        extract_verification_link,
    )

    assert ShimClient is FacadeClient
    assert ShimTransport is FacadeTransport
    assert ShimOutbound is FacadeOutbound
    assert ShimMailpitMessage is FacadeMailpitMessage
    assert ShimSummary is FacadeSummary
    assert ShimMessage is FacadeMessage
    assert ShimRecipient is FacadeRecipient
    assert ShimPayload is FacadePayload
    assert callable(build_mime_message)
    assert callable(extract_verification_link)
    assert callable(extract_verification_code)


def test_submodules_line_counts_strictly_under_limit() -> None:
    """Verify Hard Invariant 6: all submodules are strictly < 130 lines each."""
    email_pkg = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_platform"
        / "src"
        / "runefoble_platform"
        / "email"
    )
    shim_file = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_platform"
        / "src"
        / "runefoble_platform"
        / "email_client.py"
    )

    py_files = list(email_pkg.glob("*.py")) + [shim_file]
    assert len(py_files) >= 4

    for f in py_files:
        lines = len(f.read_text().splitlines())
        assert lines < 130, f"{f.name} has {lines} lines, exceeding the 130 line limit"
