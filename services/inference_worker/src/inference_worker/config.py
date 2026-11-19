"""Configuration settings for Runefoble AI Inference Worker."""

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BackendName = Literal["openai_compatible", "ollama"]


class WorkerSettings(BaseSettings):
    """Runtime configuration for inference worker."""

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_WORKER_",
        env_file=".env.worker",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service credential (ADR-0015 e). No default value. The worker refuses to start when unset.
    service_credential: SecretStr = Field(
        validation_alias=AliasChoices("RUNEFOBLE_SERVICE_CREDENTIAL"),
        description="Service credential that callers such as The Watcher must present",
    )

    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8100, description="Listen port")
    log_level: str = Field(default="INFO", description="Log level")

    backend: BackendName = Field(
        default="openai_compatible",
        description="Inference engine, selected once at start-up: openai_compatible or ollama",
    )

    # OpenAI-compatible backend (llama-swap, vLLM, llama.cpp, etc.)
    openai_base_url: str = Field(
        default="http://127.0.0.1:8080/v1",
        description="Base URL for OpenAI-compatible endpoint",
    )
    openai_model: str = Field(
        default="qwen3.8-27b-txt",
        description="Target model name on OpenAI-compatible endpoint",
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr("not-required"),
        description="API Key if needed",
    )

    # Ollama backend
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for Ollama service",
    )
    ollama_model: str = Field(
        default="qwen3.5:9b",
        description="Target Ollama model",
    )

    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    timeout_seconds: float = Field(default=30.0, gt=0.0)

    @classmethod
    def from_environment(cls) -> "WorkerSettings":
        """Load settings from the environment. Validation refuses a missing or blank credential.

        The credential comes from the environment, not from a constructor argument, so the
        type checker cannot see it. Validation still raises when it is absent.
        """
        return cls()  # type: ignore[call-arg]

    @field_validator("backend", mode="before")
    @classmethod
    def _mock_is_not_an_engine(cls, value: object) -> object:
        """Refuse `mock` in every environment. The worker has no canned engine (ADR-0015 decision 4)."""
        if value == "mock":
            raise ValueError(
                "RUNEFOBLE_WORKER_BACKEND=mock is refused in every environment. The worker has no "
                "canned engine. Use openai_compatible or ollama, or a test double at a process boundary."
            )
        return value

    @field_validator("service_credential")
    @classmethod
    def _credential_is_not_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("RUNEFOBLE_SERVICE_CREDENTIAL must not be blank")
        return value
