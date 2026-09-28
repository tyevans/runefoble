"""Pydantic schemas and request models for Gateway API Authentication."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50, description="Desired username")
    email: str = Field(description="User email address")
    password: str = Field(min_length=6, description="User password")


class TokenRequest(BaseModel):
    username: str
    password: str
    grant_type: str = "password"


class RefreshRequest(BaseModel):
    refresh_token: str
    grant_type: str = "refresh_token"


class VerifyEmailRequest(BaseModel):
    email: str
    token: str | None = None
    code: str | None = None


class DevSendEmailRequest(BaseModel):
    to: str = Field(description="Recipient email address")
    subject: str = Field(default="Runefoble Dev Email Test", description="Email subject")
    body: str = Field(
        default="This is a test email sent to Mailpit to verify SMTP dev delivery.",
        description="Email text body",
    )


# Alias for backward compatibility
TestEmailRequest = DevSendEmailRequest


class PasswordResetRequest(BaseModel):
    email: str = Field(description="User email address for password reset")
    token: str | None = Field(default=None, description="Password reset verification token")
    new_password: str | None = Field(default=None, min_length=6, description="New password")


class SeedAdminRequest(BaseModel):
    username: str = Field(default="admin", description="Admin username")
    email: str = Field(default="admin@runefoble.local", description="Admin email")
    password: str = Field(default="RunefobleAdminPassword123!", description="Admin password")


class InviteAdminRequest(BaseModel):
    email: str = Field(description="Invited admin/DM email address")
    username: str = Field(default="", description="Invited username or display name")
    role: str = Field(default="admin", description="Assigned role: admin, dm, or player")


__all__ = [
    "DevSendEmailRequest",
    "InviteAdminRequest",
    "PasswordResetRequest",
    "RefreshRequest",
    "RegisterRequest",
    "SeedAdminRequest",
    "TestEmailRequest",
    "TokenRequest",
    "VerifyEmailRequest",
]
