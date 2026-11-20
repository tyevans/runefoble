"""Request and response models for the invite account route (ADR-0023 d).

The reply is the same for a new email and an existing email. It never says which one it was.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CreateAccountRequest(BaseModel):
    invite_token: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=254)
    display_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, value: str) -> str:
        value = value.strip()
        if not EMAIL_SHAPE.fullmatch(value):
            raise ValueError("email must look like name@example.com")
        return value

    @field_validator("display_name")
    @classmethod
    def _display_name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be blank")
        return value


class AccountRequestedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    message: str = "Check your email to finish creating your account."
